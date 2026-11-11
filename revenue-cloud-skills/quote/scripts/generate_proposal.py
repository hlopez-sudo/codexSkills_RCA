#!/usr/bin/env python3
"""Generate/resume/retrieve a Context Service quote PDF through Salesforce CLI.

Uses an existing authenticated session; never reads or emits access tokens.
Expected identity must come from the connected org, not this script's defaults.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
from urllib.parse import urlencode

API = '/services/data/v68.0'
ENV = dict(os.environ, SF_DISABLE_LOG_FILE='true', SF_DISABLE_TELEMETRY='true')
# User-selected proposal, scoped to its verified org. Never substitute a namesake.
PROPOSAL_ORG = '00Dbm0000155DCXEA2'
PROPOSAL_TEMPLATE = '2dtbm000001diaAAAQ'
PROPOSAL_NAME = 'RLM_QuoteProposal_CS'
# Restored v5 bytes published as file version 7 on 2026-11-10; SHA-256 verified.
TIER_BASELINE_VERSION = '068bm00000S8TXlAAN'
TEMPLATE_CONFIG = {
    'Name': PROPOSAL_NAME, 'TokenMappingMethodType': 'ContextService',
    'ContextDefinitionName': 'RLM_QuoteDocGenContext',
    'ContextMappingName': 'QuoteDocGenMapping',
    'CustomClassName': 'RLM_QuoteUsageFormatting',
}


class ProposalError(Exception):
    pass


class ApiError(ProposalError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status
        self.ambiguous = status is None or status == 408 or status >= 500


def emit(**values):
    print(json.dumps(values), flush=True)


def sf_id(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(prefix + r'[A-Za-z0-9]{12}(?:[A-Za-z0-9]{3})?', value):
        raise ProposalError(f'Expected a {prefix} Salesforce ID')
    return value


def same_id(left, right):
    return bool(left and right and left[:15] == right[:15])


def literal(value):
    return "'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save(path, state):
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            os.chmod(temporary, 0o600)
            json.dump(state, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def journal_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + '.lock')
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ProposalError(f'Journal is locked: {lock}. Check for a running process before removing a stale lock.') from None
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def cli_json(arguments, body=None, allow_http_result=False):
    try:
        result = subprocess.run(['sf', *arguments, '--json'],
                                input=json.dumps(body) if body is not None else None,
                                capture_output=True, text=True, env=ENV, timeout=55)
    except subprocess.TimeoutExpired:
        raise ApiError('Salesforce CLI timed out; request outcome may be unknown.') from None
    except OSError as error:
        raise ApiError(f'Salesforce CLI could not run: {error.strerror}') from None
    try:
        envelope = json.loads(result.stdout)
    except ValueError:
        raise ApiError(f'Salesforce CLI returned non-JSON output (exit {result.returncode}); raw output suppressed.') from None
    if not isinstance(envelope, dict):
        raise ApiError('Salesforce CLI returned an unexpected envelope.')
    if allow_http_result and isinstance(envelope.get('result'), dict) and isinstance(envelope['result'].get('statusCode'), int):
        return envelope['result']
    if envelope.get('status') != 0:
        # Do not echo raw CLI errors, command lines, headers, or auth state.
        name = envelope.get('name', 'CLIError')
        if not isinstance(name, str) or not re.fullmatch(r'[\w.:-]{1,100}', name):
            name = 'CLIError'
        raise ApiError(f'Salesforce CLI failed ({name}); no automatic retry was made.')
    return envelope.get('result')


class Salesforce:
    def __init__(self, target, expected_org, expected_username):
        sf_id(expected_org, '00D')
        if not same_id(expected_org, PROPOSAL_ORG):
            raise ProposalError('The selected usage-tier proposal is configured only for its verified org.')
        sessions = cli_json(['org', 'list', 'auth'])
        if not isinstance(sessions, list):
            raise ProposalError('Cannot inspect existing Salesforce CLI sessions.')
        matches = [entry for entry in sessions if
                   target in [entry.get('username'), *(entry.get('alias') or '').split(',')]
                   and entry.get('username') == expected_username
                   and same_id(entry.get('orgId'), expected_org)]
        if len(matches) != 1:
            raise ProposalError('No unique existing CLI session matches the target, connected org ID, and connected username.')
        self.username = expected_username  # Pin the resolved username, not a mutable/default alias.
        self.org_id = expected_org
        self.api_calls = 0

    def request(self, path, method='GET', body=None):
        if not path.startswith(API + '/'):
            raise ProposalError('Only the documented v68.0 relative API paths are supported.')
        arguments = ['api', 'request', 'rest', path, '--target-org', self.username,
                     '--method', method]
        if body is not None:
            arguments += ['--body', '-', '--header', 'Content-Type:application/json']
        self.api_calls += 1
        result = cli_json(arguments, body, allow_http_result=True)
        if not isinstance(result, dict) or not isinstance(result.get('statusCode'), int):
            raise ApiError('REST response did not include an HTTP status.')
        status, payload = result['statusCode'], result.get('body')
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except ValueError:
                raise ApiError('REST returned a non-JSON response.', status) from None
        if not 200 <= status < 300:
            errors = payload if isinstance(payload, list) else [payload]
            details = [{k: item.get(k) for k in ('errorCode', 'message', 'fields') if k in item}
                       for item in errors if isinstance(item, dict)]
            raise ApiError(f'HTTP {status}: {json.dumps(details)}', status)
        return status, payload

    def query(self, soql):
        _, payload = self.request(API + '/query?' + urlencode({'q': soql}))
        if not isinstance(payload, dict) or payload.get('done') is not True:
            raise ProposalError('Query was incomplete or returned an unexpected response.')
        return payload['records']

    def download(self, version_id, destination):
        sf_id(version_id, '068')
        # Construct from the validated ID; never send credentials to a supplied URL.
        self.api_calls += 1
        cli_json(['api', 'request', 'rest', API + '/sobjects/ContentVersion/' + version_id + '/VersionData',
                  '--target-org', self.username, '--stream-to-file', str(destination)])


def one(records, description):
    if len(records) != 1:
        raise ProposalError(f'Expected one {description}; found {len(records)}.')
    return records[0]


def prepare(client, quote_id, template_name, output_dir, priced_quote_number=None):
    sf_id(quote_id, '0Q0')
    if template_name != PROPOSAL_NAME:
        raise ProposalError('Only the selected RLM_QuoteProposal_CS usage-tier proposal is supported.')
    if priced_quote_number is not None:
        if not re.fullmatch(r'[0-9]{1,30}', priced_quote_number):
            raise ProposalError('Expected the quote number from a completed pricing verification.')
        quote = {'QuoteNumber': priced_quote_number}
    else:
        quote = one(client.query('SELECT Id,QuoteNumber,CalculationStatus,LastModifiedDate '
                                 'FROM Quote WHERE Id=' + literal(quote_id)), 'quote')
        if quote.get('CalculationStatus') != 'CompletedWithPricing':
            raise ProposalError('Quote pricing is unfinished; resolve pricing before generation.')
    template = one(client.query('SELECT Id,Name,TokenMappingMethodType,ContextDefinitionName,'
                               'ContextMappingName,CustomClassName FROM DocumentTemplate WHERE Id='
                               + literal(PROPOSAL_TEMPLATE) + ' AND Name=' + literal(PROPOSAL_NAME)
                               + " AND IsActive=true AND Status='Active' LIMIT 2"), 'selected active template')
    if not same_id(template.get('Id'), PROPOSAL_TEMPLATE) or any(
            template.get(key) != value for key, value in TEMPLATE_CONFIG.items()):
        raise ProposalError('The selected usage-tier template configuration has changed; no substitute was requested.')
    template_id = sf_id(template['Id'], '2dt')
    source = one(client.query('SELECT LatestContentVersionId FROM DocumentTemplateContentDoc '
                             'WHERE DocumentTemplateId=' + literal(template_id)
                             + " AND FileStageType='Original' LIMIT 2"), 'original template file')
    version_id = sf_id(source['LatestContentVersionId'], '068')
    title = 'Quote-' + quote['QuoteNumber'] + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    body = {'Type': 'GenerateAndConvert', 'ReferenceObject': quote_id,
            'DocumentTemplateId': template_id, 'DocumentInputType': 'DocumentTemplate',
            'DocGenApiVersionType': 'Advanced', 'DocGenAdditionalInputType': 'ContextService',
            'DocGenAdditionalInput': quote_id,
            'RequestText': json.dumps({'keepIntermediate': True, 'title': title,
                                      'templateContentVersionId': version_id}, separators=(',', ':'))}
    if len(body['RequestText']) > 255:
        raise ProposalError('RequestText exceeds the verified v68.0 field length.')
    return {'journalVersion': 1, 'orgId': client.org_id, 'username': client.username,
            'apiVersion': '68.0', 'quoteId': quote_id, 'quoteNumber': quote['QuoteNumber'],
            'quoteModifiedAt': quote.get('LastModifiedDate'), 'templateId': template_id,
            'templateVersionId': version_id, 'outputDir': str(output_dir.resolve()),
            'title': title, 'request': body}


def submit(client, path, state):
    state.update(stage='submitting', submittedAt=utc_now())
    save(path, state)  # Durable before the only mutating API call.
    try:
        status, result = client.request(API + '/sobjects/DocumentGenerationProcess', 'POST', state['request'])
        if status != 201 or not isinstance(result, dict) or result.get('success') is not True or result.get('errors'):
            raise ApiError('Create response did not confirm HTTP 201, success, and empty errors.')
        process_id = sf_id(result.get('id'), '0nn')
    except (ApiError, ProposalError) as error:
        state['stage'] = 'rejected' if isinstance(error, ApiError) and not error.ambiguous else 'uncertain'
        state['submissionDiagnostic'] = str(error)
        save(path, state)
        raise
    state.update(stage='submitted', processId=process_id, createHttpStatus=status)
    save(path, state)
    emit(event='submitted', processId=process_id, httpStatus=status)


def recover(client, path, state):
    if state.get('processId'):
        sf_id(state['processId'], '0nn')
        return
    if state.get('stage') not in ('submitting', 'uncertain'):
        raise ProposalError('No resumable submission. A rejected request is not automatically retried.')
    start = datetime.fromisoformat(state['submittedAt']) - timedelta(seconds=60)
    since = start.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    query = ('SELECT Id,ReferenceObject,DocumentTemplateId,RequestText FROM DocumentGenerationProcess WHERE '
             'ReferenceObject=' + literal(state['quoteId']) + ' AND DocumentTemplateId=' + literal(state['templateId'])
             + ' AND RequestText=' + literal(state['request']['RequestText']) + ' AND CreatedDate>=' + since + ' LIMIT 2')
    matches = client.query(query)
    matches = [row for row in matches if same_id(row.get('ReferenceObject'), state['quoteId'])
               and same_id(row.get('DocumentTemplateId'), state['templateId'])
               and row.get('RequestText') == state['request']['RequestText']]
    if len(matches) != 1:
        raise ProposalError(f'Uncertain submission: found {len(matches)} exact matching processes; no replacement was submitted.')
    state.update(stage='submitted', processId=sf_id(matches[0]['Id'], '0nn'))
    save(path, state)
    emit(event='recovered', processId=state['processId'])


def inspect_pdf(path, expected_size):
    data = path.read_bytes()
    if not data.startswith(b'%PDF-') or not data:
        raise ProposalError('Downloaded content is not a PDF; HTML/login/error responses are not deliverables.')
    if len(data) != expected_size:
        raise ProposalError(f'PDF size mismatch: expected {expected_size}, received {len(data)}.')
    return {'path': str(path.resolve()), 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def verify_new_template_version(journal_path, state, pdf_path):
    """Only a new source version needs a targeted text check; never render pages."""
    version_id = sf_id(state.get('templateVersionId'), '068')
    if same_id(version_id, TIER_BASELINE_VERSION):
        return
    cache_path = journal_path.parent / 'proposal-usage-template-verification.json'
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    if not (same_id(cache.get('orgId'), state['orgId']) and
            same_id(cache.get('templateId'), PROPOSAL_TEMPLATE)):
        cache = {'orgId': state['orgId'], 'templateId': PROPOSAL_TEMPLATE, 'versions': {}}
    if version_id[:15] in cache.get('versions', {}):
        return
    try:
        result = subprocess.run(['pdftotext', str(pdf_path), '-'], capture_output=True,
                                text=True, timeout=20)
    except FileNotFoundError:
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ProposalError('New template version needs a usage-tier text check. PDF is saved; '
                                'resume with a Python runtime containing pypdf or provide pdftotext.') from None
        try:
            extracted = '\n'.join(page.extract_text() or '' for page in PdfReader(pdf_path).pages)
        except Exception:
            raise ProposalError('Cannot extract text for the new template version. PDF is saved for review.') from None
    except (OSError, subprocess.TimeoutExpired):
        raise ProposalError('New template version needs a usage-tier text check. PDF is saved; '
                            'resolve the text-reader error, then resume without regenerating.') from None
    else:
        if result.returncode:
            raise ProposalError('Cannot extract text for the new template version. PDF is saved for review.')
        extracted = result.stdout
    normalized = ' '.join(extracted.casefold().split())
    required = ['usage rates and grants', 'schedule bounds', 'lower bound', 'upper bound', 'adjustment']
    if any(term not in normalized for term in required):
        raise ProposalError('Cannot confirm usage-tier tables for the new template version. '
                            'PDF is saved for review; do not regenerate or substitute a template.')
    cache.setdefault('versions', {})[version_id[:15]] = {
        'verifiedAt': utc_now(), 'processId': state['processId'], 'pdfSha256': state['download']['sha256']}
    save(cache_path, cache)


def retrieve_pdf(client, path, state, response_text):
    started = time.monotonic()
    versions = [part.strip() for part in response_text.split(',')] if isinstance(response_text, str) else []
    if not versions or any(not part for part in versions):
        raise ProposalError('Success response did not contain ContentVersion IDs.')
    versions = list(dict.fromkeys(sf_id(value, '068') for value in versions))
    records = client.query('SELECT Id,ContentDocumentId,Title,FileExtension,ContentSize FROM ContentVersion WHERE Id IN ('
                           + ','.join(literal(value) for value in versions) + ')')
    pdf = one([row for row in records if str(row.get('FileExtension', '')).lower() == 'pdf'], 'generated PDF version')
    version_id = sf_id(pdf['Id'], '068')
    document_id = sf_id(pdf['ContentDocumentId'], '069')
    if not any(same_id(version_id, candidate) for candidate in versions):
        raise ProposalError('PDF version was not returned by the generation process.')
    expected_size = pdf.get('ContentSize')
    if not isinstance(expected_size, int) or expected_size <= 0:
        raise ProposalError('PDF metadata has no positive ContentSize.')
    state.update(pdfContentVersionId=version_id, pdfContentDocumentId=document_id,
                 outputProvenance='matching-process-response', stage='downloading')
    save(path, state)
    output_dir = Path(state['outputDir'])
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / ('quote-' + state['quoteId'] + '-' + state['processId'] + '.pdf')
    if destination.exists():
        details = inspect_pdf(destination, expected_size)
        if state.get('download', {}).get('sha256') != details['sha256']:
            raise ProposalError('Output already exists without matching journal evidence; choose another output directory.')
    else:
        temporary = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.part')
        try:
            client.download(version_id, temporary)
            details = inspect_pdf(temporary, expected_size)
            # Atomic publication without overwriting another file.
            os.link(temporary, destination)
            details['path'] = str(destination.resolve())
        finally:
            temporary.unlink(missing_ok=True)
    state.update(stage='downloaded-unverified', download=details, downloadedAt=utc_now())
    save(path, state)
    verify_new_template_version(path, state, destination)
    state.update(stage='downloaded', readyAt=utc_now(), usageTierTemplateVerified=True)
    state.setdefault('timingsSeconds', {})['retrieval'] = round(time.monotonic() - started, 3)
    save(path, state)
    return {'outcome': 'downloaded', 'processId': state['processId'], 'pdfContentVersionId': version_id,
            'templateId': state['templateId'], 'templateVersionId': state['templateVersionId'], **details}


def finish(client, path, state, wait_seconds):
    deadline = time.monotonic() + wait_seconds
    previous = None
    while True:
        record = one(client.query('SELECT Id,Status,ReferenceObject,DocumentTemplateId,RequestText,ResponseText '
                                  'FROM DocumentGenerationProcess WHERE Id=' + literal(state['processId'])),
                     'generation process')
        if not same_id(record.get('Id'), state['processId']) or not same_id(record.get('ReferenceObject'), state['quoteId']):
            raise ProposalError('Generation process does not belong to the requested quote.')
        if state.get('templateId') and not same_id(record.get('DocumentTemplateId'), state['templateId']):
            raise ProposalError('Generation process uses a different template than the journal.')
        if not same_id(record.get('DocumentTemplateId'), PROPOSAL_TEMPLATE):
            raise ProposalError('Generation process is not for the selected usage-tier proposal.')
        state['templateId'] = PROPOSAL_TEMPLATE
        try:
            inputs = json.loads(record.get('RequestText') or '')
            source_version = sf_id(inputs.get('templateContentVersionId'), '068')
        except (ValueError, AttributeError):
            raise ProposalError('Cannot verify the template source version from the generation process.') from None
        if state.get('templateVersionId') and not same_id(source_version, state['templateVersionId']):
            raise ProposalError('Generation process uses a different template source version than the journal.')
        state['templateVersionId'] = source_version
        status, response = record.get('Status'), record.get('ResponseText')
        state.update(generationStatus=status, responseText=response, lastPollAt=utc_now())
        save(path, state)
        if status != previous:
            emit(event='status', processId=state['processId'], status=status)
            previous = status
        if status == 'Success':
            if state.get('submittedAt') and 'generationObserved' not in state.setdefault('timingsSeconds', {}):
                elapsed = datetime.fromisoformat(state['lastPollAt']) - datetime.fromisoformat(state['submittedAt'])
                state['timingsSeconds']['generationObserved'] = round(elapsed.total_seconds(), 3)
            return retrieve_pdf(client, path, state, response)
        if status in ('Failure', 'Blocked'):
            return {'outcome': status.lower(), 'processId': state['processId'], 'diagnostic': response}
        if status not in ('Waiting', 'InProgress'):
            raise ProposalError(f'Unknown process status: {status!r}; no replacement was submitted.')
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {'outcome': 'pending', 'processId': state['processId'], 'status': status}
        time.sleep(min(4, remaining))


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest='command', required=True)
    for name in ('generate', 'resume', 'retrieve'):
        sub = commands.add_parser(name)
        sub.add_argument('--target-org', required=True, help='Existing CLI username or alias; never uses the default org')
        sub.add_argument('--expected-org-id', required=True, help='Org ID independently obtained through the connected MCP')
        sub.add_argument('--expected-username', required=True, help='Connected username independently established before fallback')
        sub.add_argument('--state', type=Path, required=True, help='Unique request journal; reuse it to resume')
        sub.add_argument('--output-dir', type=Path, required=name != 'resume')
        sub.add_argument('--wait-seconds', type=int, default=45, choices=range(0, 56), metavar='0..55')
        if name != 'resume':
            sub.add_argument('--quote-id', required=True)
        if name == 'generate':
            sub.add_argument('--template-name', default=PROPOSAL_NAME, choices=[PROPOSAL_NAME])
            sub.add_argument('--priced-quote-number', help='Reuse this quote number only after '
                             'CompletedWithPricing was verified for this quote in the current connected session')
        if name == 'retrieve':
            sub.add_argument('--process-id', required=True, help='Existing process; this command never generates a document')
    return result


def run(args, client_factory=Salesforce):
    started = time.monotonic()
    path = args.state.resolve()
    with journal_lock(path):
        if args.command != 'resume' and path.exists():
            raise ProposalError('Journal already exists. Use resume, not a new submission.')
        if args.command == 'resume' and not path.exists():
            raise ProposalError('Journal does not exist. Use retrieve for a known existing process.')
        state = json.loads(path.read_text()) if args.command == 'resume' else None
        if state and (state.get('journalVersion') != 1 or state.get('apiVersion') != '68.0'
                      or not same_id(state.get('orgId'), args.expected_org_id)
                      or state.get('username') != args.expected_username):
            raise ProposalError('Journal version or identity does not match this request.')
        if state and state.get('templateId') and not same_id(state['templateId'], PROPOSAL_TEMPLATE):
            raise ProposalError('Journal is not for the selected usage-tier proposal.')
        client = client_factory(args.target_org, args.expected_org_id, args.expected_username)
        if args.command == 'generate':
            state = prepare(client, args.quote_id, args.template_name, args.output_dir, args.priced_quote_number)
            state['timingsSeconds'] = {'preparation': round(time.monotonic() - started, 3)}
            submitting = time.monotonic()
            submit(client, path, state)
            state['timingsSeconds']['submission'] = round(time.monotonic() - submitting, 3)
        elif args.command == 'retrieve':
            state = {'journalVersion': 1, 'apiVersion': '68.0', 'orgId': client.org_id,
                     'username': client.username, 'quoteId': sf_id(args.quote_id, '0Q0'),
                     'processId': sf_id(args.process_id, '0nn'),
                    'templateId': PROPOSAL_TEMPLATE,
                     'outputDir': str(args.output_dir.resolve()), 'stage': 'retrieving'}
            save(path, state)
        else:
            if args.output_dir:
                state['outputDir'] = str(args.output_dir.resolve())
            recover(client, path, state)
        result = finish(client, path, state, args.wait_seconds)
        state['lastInvocationSeconds'] = round(time.monotonic() - started, 3)
        state['lastInvocationApiCalls'] = client.api_calls
        save(path, state)
        return {**result, 'timingsSeconds': state.get('timingsSeconds', {}),
                'invocationSeconds': state['lastInvocationSeconds'], 'apiCalls': client.api_calls}


def main():
    args = parser().parse_args()
    try:
        result = run(args)
        emit(**result)
        return 2 if result['outcome'] in ('failure', 'blocked') else 0
    except (ProposalError, OSError, ValueError, KeyError) as error:
        emit(outcome='error', diagnostic=str(error), journal=str(args.state.resolve()))
        return 1


if __name__ == '__main__':
    sys.exit(main())
