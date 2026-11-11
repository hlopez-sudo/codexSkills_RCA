import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(os.environ.get('QUOTE_HELPER_PATH', Path(__file__).with_name('generate_proposal.py')))
spec = importlib.util.spec_from_file_location('proposal_helper', SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

def sid(prefix, digit='1'):
    return prefix + '0' * 11 + digit + 'AAA'

ORG, TEMPLATE, SOURCE = helper.PROPOSAL_ORG, helper.PROPOSAL_TEMPLATE, helper.TIER_BASELINE_VERSION
QUOTE, PROCESS = sid('0Q0'), sid('0nn')
PDF, WORD, DOCUMENT = sid('068','2'), sid('068','3'), sid('069')
USERNAME = 'fixture@example.invalid'
PDF_BYTES = b'%PDF-1.7\nfixture-body\n%%EOF\n'


class FakeCLI:
    """Exercise the actual CLI adapter, payload and state machine without network."""
    def __init__(self, scenario='success'):
        self.scenario = scenario
        self.posts = []
        self.downloads = 0
        self.calls = []
        self.process_reads = 0
        self.source = SOURCE
        self.text_checks = 0

    def __call__(self, command, **kwargs):
        from urllib.parse import parse_qs, urlsplit
        self.calls.append(command)
        if command[0] == 'pdftotext':
            self.text_checks += 1
            if self.scenario == 'missing_pdftotext':
                raise FileNotFoundError()
            text = 'USAGE RATES AND GRANTS Schedule bounds Lower bound Upper bound Adjustment'
            if self.scenario == 'missing_tiers':
                text = 'Generic quote without rates'
            return subprocess.CompletedProcess(command,0,stdout=text,stderr='')
        if command[:4] == ['sf','org','list','auth']:
            org = sid('00D','9') if self.scenario == 'identity_mismatch' else ORG
            body = [{'username':USERNAME, 'orgId':org, 'alias':'fixture'}]
            return self.reply(body)
        path = command[4]
        self.target = command[command.index('--target-org')+1]
        assert self.target == USERNAME, 'Must pin explicit resolved username'
        if '--stream-to-file' in command:
            self.downloads += 1
            content = PDF_BYTES
            if self.scenario == 'html':
                content = b'<html>' + b'x' * (len(PDF_BYTES)-6)
            if self.scenario == 'truncated':
                content = PDF_BYTES[:9]
            Path(command[command.index('--stream-to-file')+1]).write_bytes(content)
            return self.reply({'statusCode':0,'body':''})
        if '/query?' in path:
            q = parse_qs(urlsplit(path).query)['q'][0]
            if 'FROM Quote ' in q:
                rows = [{'Id':QUOTE,'QuoteNumber':'00000001','Name':'Fixture Quote',
                         'CalculationStatus':('Pending' if self.scenario == 'unpriced' else 'CompletedWithPricing'),'LastModifiedDate':'2026-11-03T00:00:00Z'}]
            elif 'FROM DocumentTemplateContentDoc ' in q:
                rows = [{'LatestContentVersionId':self.source}]
            elif 'FROM DocumentTemplate ' in q:
                rows = [{'Id':TEMPLATE,**helper.TEMPLATE_CONFIG}]
                if self.scenario == 'wrong_template':
                    rows[0]['Id'] = sid('2dt','9')
                if self.scenario == 'wrong_formatter':
                    rows[0]['CustomClassName'] = 'GenericFormatter'
                if self.scenario == 'missing_template':
                    rows = []
            elif 'FROM DocumentGenerationProcess WHERE Id=' in q:
                rows = [self.process_record()]
            elif 'FROM DocumentGenerationProcess ' in q:
                self.recovery_query = q
                rows = [] if self.scenario == 'ambiguous_no_match' else [
                    {'Id':PROCESS,'ReferenceObject':QUOTE,'DocumentTemplateId':TEMPLATE,
                     'RequestText':self.posts[0]['RequestText']}]
            elif 'FROM ContentVersion ' in q:
                rows = [{'Id':WORD,'FileExtension':'docx','ContentDocumentId':sid('069','2'),'ContentSize':100},
                        {'Id':PDF,'FileExtension':'pdf','ContentDocumentId':DOCUMENT,'ContentSize':len(PDF_BYTES)}]
                if self.scenario == 'no_pdf':
                    rows = rows[:1]
            else:
                raise AssertionError(q)
            return self.http(200, {'done':True, 'totalSize':len(rows), 'records':rows})
        if path.endswith('/sobjects/DocumentGenerationProcess'):
            payload = json.loads(kwargs['input'])
            self.posts.append(payload)
            if self.scenario.startswith('ambiguous'):
                return subprocess.CompletedProcess(command, 1, stdout='not json', stderr='')
            if self.scenario == 'rejection':
                return self.http(400,[{'errorCode':'FUNCTIONALITY_NOT_ENABLED','message':'insert unsupported'}],1)
            return self.http(201, {'id':PROCESS,'success':True,'errors':[]})
        raise AssertionError(command)

    def process_record(self):
        self.process_reads += 1
        status = {'pending':'Waiting','blocked':'Blocked','failure':'Failure','unknown':'Unexpected'}.get(self.scenario,'Success')
        if self.scenario == 'delayed' and self.process_reads == 1:
            status = 'InProgress'
        quote = sid('0Q0','9') if self.scenario == 'wrong_quote' else QUOTE
        template = sid('2dt','9') if self.scenario == 'wrong_process_template' else TEMPLATE
        request = self.posts[-1]['RequestText'] if self.posts else json.dumps({'templateContentVersionId':self.source})
        if self.scenario == 'wrong_source':
            request = json.dumps({'templateContentVersionId':sid('068','9')})
        if self.scenario == 'missing_request':
            request = ''
        return {'Id':PROCESS,'ReferenceObject':quote,'DocumentTemplateId':template,
                          'RequestText':request,'Status':status,'ResponseText':WORD if status == 'InProgress' else WORD+','+PDF}

    def reply(self, body, status=0):
        return subprocess.CompletedProcess([],status,stdout=json.dumps({'status':status,'result':body}),stderr='')

    def http(self, status, body, cli_status=0):
        return self.reply({'statusCode':status,'body':body},cli_status)


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.fake = FakeCLI()
        self.patch = patch.object(helper.subprocess,'run',self.fake)
        self.patch.start()
        self.silence = contextlib.redirect_stdout(io.StringIO())
        self.silence.__enter__()

    def tearDown(self):
        self.silence.__exit__(None,None,None)
        self.patch.stop()
        self.directory.cleanup()

    def args(self, command='generate'):
        args = [command,'--target-org','fixture','--expected-org-id',ORG,'--expected-username',USERNAME,
                '--state',str(self.root/'state.json'),'--wait-seconds','0']
        if command != 'resume':
            args += ['--quote-id',QUOTE,'--output-dir',str(self.root/'outputs')]
        if command == 'generate':
            args += ['--priced-quote-number','00000001']
        if command == 'retrieve':
            args += ['--process-id',PROCESS]
        return helper.parser().parse_args(args)

    def state(self):
        return json.loads((self.root/'state.json').read_text())

    def test_generate_download_resume_without_duplicate(self):
        result = helper.run(self.args())
        self.assertEqual(result['outcome'],'downloaded')
        self.assertEqual(Path(result['path']).read_bytes(),PDF_BYTES)
        self.assertEqual(len(self.fake.posts),1)
        body = self.fake.posts[0]
        self.assertEqual(body['DocGenAdditionalInput'],QUOTE)
        self.assertEqual(json.loads(body['RequestText'])['templateContentVersionId'],SOURCE)
        self.assertLessEqual(len(body['RequestText']),255)
        helper.run(self.args('resume'))
        self.assertEqual(len(self.fake.posts),1)
        self.assertEqual(self.fake.downloads,1)
        with self.assertRaises(helper.ProposalError):
            helper.run(self.args())

    def test_pending_ignores_partial_response_then_resume(self):
        self.fake.scenario='delayed'
        self.assertEqual(helper.run(self.args())['outcome'],'pending')
        self.assertEqual(self.fake.downloads,0)
        self.assertEqual(helper.run(self.args('resume'))['outcome'],'downloaded')
        self.assertEqual(len(self.fake.posts),1)

    def test_ambiguous_post_recovers_exact_match(self):
        self.fake.scenario='ambiguous_match'
        with self.assertRaises(helper.ApiError):
            helper.run(self.args())
        self.assertEqual(self.state()['stage'],'uncertain')
        result=helper.run(self.args('resume'))
        self.assertEqual(result['outcome'],'downloaded')
        self.assertEqual(len(self.fake.posts),1)
        for field in ['RequestText=','ReferenceObject=','DocumentTemplateId=','CreatedDate>=']:
            self.assertIn(field,self.fake.recovery_query)

    def test_ambiguous_without_match_does_not_resubmit(self):
        self.fake.scenario='ambiguous_no_match'
        with self.assertRaises(helper.ApiError):
            helper.run(self.args())
        with self.assertRaises(helper.ProposalError):
            helper.run(self.args('resume'))
        self.assertEqual(len(self.fake.posts),1)

    def test_definite_http_rejection_preserves_diagnostic(self):
        self.fake.scenario='rejection'
        with self.assertRaisesRegex(helper.ApiError,'FUNCTIONALITY_NOT_ENABLED'):
            helper.run(self.args())
        self.assertEqual(self.state()['stage'],'rejected')
        with self.assertRaises(helper.ProposalError):
            helper.run(self.args('resume'))
        self.assertEqual(len(self.fake.posts),1)

    def test_retrieve_never_submits(self):
        self.assertEqual(helper.run(self.args('retrieve'))['outcome'],'downloaded')
        self.assertEqual(self.fake.posts,[])

    def test_terminal_and_unknown_states(self):
        for scenario in ['blocked','failure','pending','unknown']:
            with self.subTest(scenario=scenario):
                (self.root/'state.json').unlink(missing_ok=True)
                self.fake.scenario=scenario
                if scenario == 'unknown':
                    with self.assertRaises(helper.ProposalError):
                        helper.run(self.args())
                else:
                    self.assertEqual(helper.run(self.args())['outcome'],scenario)
                self.assertEqual(self.fake.downloads,0)

    def test_identity_and_template_fail_before_post(self):
        for scenario in ['identity_mismatch','wrong_template','wrong_formatter','missing_template']:
            with self.subTest(scenario=scenario):
                self.fake.scenario=scenario
                with self.assertRaises(helper.ProposalError):
                    helper.run(self.args())
                self.assertEqual(self.fake.posts,[])

    def test_wrong_quote_template_request_and_missing_pdf(self):
        for scenario in ['wrong_quote','wrong_process_template','missing_request','no_pdf']:
            with self.subTest(scenario=scenario):
                (self.root/'state.json').unlink(missing_ok=True)
                self.fake.scenario=scenario
                with self.assertRaises(helper.ProposalError):
                    helper.run(self.args('retrieve'))
                self.assertEqual(self.fake.downloads,0)

    def test_corrupt_download_is_not_published_and_can_resume(self):
        for scenario in ['html','truncated']:
            with self.subTest(scenario=scenario):
                (self.root/'state.json').unlink(missing_ok=True)
                self.fake.scenario=scenario
                with self.assertRaises(helper.ProposalError):
                    helper.run(self.args('retrieve'))
                self.assertEqual(list((self.root/'outputs').iterdir()),[])
        self.fake.scenario='success'
        self.assertEqual(helper.run(self.args('resume'))['outcome'],'downloaded')
        self.assertEqual(self.fake.posts,[])

    def test_journal_lock_blocks_concurrent_execution(self):
        path=self.root/'state.json'
        with helper.journal_lock(path):
            with self.assertRaises(helper.ProposalError):
                helper.run(self.args())
        self.assertEqual(self.fake.posts,[])

    def test_warm_path_api_budget_and_timing(self):
        result = helper.run(self.args())
        self.assertEqual(result['apiCalls'],6)
        self.assertEqual(self.fake.text_checks,0)
        self.assertEqual(set(result['timingsSeconds']),
                         {'preparation','submission','generationObserved','retrieval'})
        self.assertTrue(all(v >= 0 for v in result['timingsSeconds'].values()))
        self.assertFalse(any('FROM+Quote+' in str(call) for call in self.fake.calls))
        self.assertEqual(result['templateId'],TEMPLATE)
        self.assertEqual(result['templateVersionId'],SOURCE)

    def test_no_pricing_evidence_reads_quote_once(self):
        args = self.args()
        args.priced_quote_number = None
        result = helper.run(args)
        self.assertEqual(result['apiCalls'],7)
        (self.root/'state.json').unlink()
        self.fake.scenario = 'unpriced'
        with self.assertRaisesRegex(helper.ProposalError,'pricing is unfinished'):
            helper.run(args)
        self.assertEqual(len(self.fake.posts),1)

    def test_other_org_and_other_template_argument_are_rejected(self):
        args = self.args()
        args.expected_org_id = sid('00D','9')
        with self.assertRaisesRegex(helper.ProposalError,'verified org'):
            helper.run(args)
        args = self.args()
        args.template_name = 'Generic_Quote'
        with self.assertRaisesRegex(helper.ProposalError,'Only the selected'):
            helper.run(args)
        self.assertEqual(self.fake.posts,[])

    def test_new_source_version_checks_tiers_once_and_is_used_in_post(self):
        self.fake.source = sid('068','7')
        result = helper.run(self.args())
        self.assertEqual(result['outcome'],'downloaded')
        self.assertEqual(self.fake.text_checks,1)
        self.assertEqual(json.loads(self.fake.posts[0]['RequestText'])['templateContentVersionId'],self.fake.source)
        helper.run(self.args('resume'))
        self.assertEqual(self.fake.text_checks,1)
        (self.root/'state.json').unlink()
        args = self.args()
        args.output_dir = self.root/'second-output'
        helper.run(args)
        self.assertEqual(self.fake.text_checks,1)
        self.fake.source = sid('068','8')
        (self.root/'state.json').unlink()
        args.output_dir = self.root/'third-output'
        helper.run(args)
        self.assertEqual(self.fake.text_checks,2)

    def test_new_source_missing_tiers_retains_pdf_then_resumes_without_post(self):
        for scenario in ['missing_tiers','missing_pdftotext']:
            with self.subTest(scenario=scenario):
                (self.root/'state.json').unlink(missing_ok=True)
                self.fake.source = sid('068','7')
                self.fake.scenario = scenario
                with self.assertRaises(helper.ProposalError):
                    helper.run(self.args('retrieve'))
                self.assertEqual(self.state()['stage'],'downloaded-unverified')
                self.assertTrue(Path(self.state()['download']['path']).exists())
                self.assertEqual(self.fake.posts,[])
                # Remove the verified fixture file to start the next independent case.
                Path(self.state()['download']['path']).unlink()
        self.fake.scenario = 'success'
        self.assertEqual(helper.run(self.args('resume'))['outcome'],'downloaded')
        self.assertEqual(self.fake.posts,[])

    def test_process_source_mismatch_stops_before_download(self):
        self.fake.scenario = 'wrong_source'
        with self.assertRaisesRegex(helper.ProposalError,'source version'):
            helper.run(self.args())
        self.assertEqual(self.fake.downloads,0)

    def test_template_cache_cannot_cross_org_or_template(self):
        self.fake.source = sid('068','7')
        (self.root/'proposal-usage-template-verification.json').write_text(json.dumps({
            'orgId':sid('00D','9'),'templateId':TEMPLATE,
            'versions':{self.fake.source[:15]:{'verifiedAt':'irrelevant'}}}))
        helper.run(self.args())
        self.assertEqual(self.fake.text_checks,1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
