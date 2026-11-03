import copy
import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / 'plugins/filter/argocd_bootstrap.py'
spec = importlib.util.spec_from_file_location('argocd_bootstrap', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def app(name, phase='Succeeded', sync='Synced', health='Healthy'):
    return {'metadata': {'name': name, 'resourceVersion': '123'},
            'status': {'sync': {'status': sync, 'revision': 'known-commit'},
                       'health': {'status': health}, 'operationState': {'phase': phase}}}


def snapshot():
    return {'api_ok': True, 'platform_stable': True, 'poll': 10, 'counts': {},
            'max_recovery': 3, 'cooldown': 5, 'parent': app('app-of-apps'),
            'apps': [app('rhacs-operator')],
            'pools': [{'status': {'conditions': [
                {'type': 'Updated', 'status': 'True'},
                {'type': 'Updating', 'status': 'False'},
                {'type': 'Degraded', 'status': 'False'}]}}],
            'pods': [{'metadata': {'name': 'openshift-gitops-' + name},
                      'status': {'conditions': [{'type': 'Ready', 'status': 'True'}]}}
                     for name in ('repo-server-test', 'application-controller-0')]}


class BootstrapRecoveryTests(unittest.TestCase):
    def state(self, s):
        return module.bootstrap_state(s)

    def test_healthy_snapshot_passes(self):
        self.assertTrue(self.state(snapshot())['ready'])

    def test_no_apps_or_failed_api_never_passes(self):
        for key, value in [('apps', []), ('api_ok', False), ('parent', {})]:
            s = snapshot()
            s[key] = value
            self.assertFalse(self.state(s)['ready'])

    def test_failed_hook_cannot_hide_behind_healthy_status(self):
        s = snapshot()
        s['apps'][0]['status']['operationState']['phase'] = 'Failed'
        out = self.state(s)
        self.assertFalse(out['ready'])
        self.assertEqual(out['recover'][0]['revision'], 'known-commit')
        self.assertNotIn('status', out['recover'][0])
        self.assertNotIn('spec', out['recover'][0])

    def test_active_operation_is_never_overwritten(self):
        for phase in ('Running', 'Terminating'):
            s = snapshot()
            s['apps'][0] = app('rhacs-operator', phase, 'OutOfSync')
            self.assertEqual(self.state(s)['recover'], [])
        s = snapshot()
        s['apps'][0] = app('rhacs-operator', 'Failed', 'OutOfSync')
        s['apps'][0]['operation'] = {'sync': {}}
        self.assertEqual(self.state(s)['recover'], [])

    def test_recovery_waits_for_machineconfig_and_gitops_stability(self):
        s = snapshot()
        s['apps'][0] = app('rhacs-operator', 'Error', 'OutOfSync')
        for key, value in [('pools', []), ('pods', []), ('platform_stable', False)]:
            delayed = copy.deepcopy(s)
            delayed[key] = value
            self.assertEqual(self.state(delayed)['recover'], [])
        s['pools'][0]['status']['conditions'][1]['status'] = 'True'
        self.assertEqual(self.state(s)['recover'], [])

    def test_retry_budget_and_cooldown_are_enforced(self):
        s = snapshot()
        s['apps'][0] = app('rhacs-operator', 'Failed', 'OutOfSync')
        for count, last_poll in [(3, 0), (1, 8)]:
            s['counts'] = {'rhacs-operator': {'count': count, 'last_poll': last_poll}}
            self.assertEqual(self.state(s)['recover'], [])
        s['counts'] = {'rhacs-operator': {'count': 2, 'last_poll': 4}}
        self.assertEqual(len(self.state(s)['recover']), 1)

    def test_healthy_progressing_apps_are_not_restarted(self):
        s = snapshot()
        s['apps'][0] = app('rhacs-operator', 'Succeeded', 'Synced', 'Progressing')
        self.assertFalse(self.state(s)['ready'])
        self.assertEqual(self.state(s)['recover'], [])

    def test_parent_can_be_recovered(self):
        s = snapshot()
        s['parent'] = app('app-of-apps', 'Error', 'OutOfSync')
        self.assertEqual(self.state(s)['recover'][0]['name'], 'app-of-apps')

    def test_multisource_revision_set_is_preserved(self):
        s = snapshot()
        a = app('roadshow-demo-apps', 'Error', 'OutOfSync')
        a['status']['sync'].pop('revision')
        a['status']['sync']['revisions'] = ['external-sha', 'gitops-sha']
        s['apps'] = [a]
        candidate = self.state(s)['recover'][0]
        self.assertEqual(candidate['revisions'], ['external-sha', 'gitops-sha'])
        self.assertNotIn('revision', candidate)

    def test_recovery_batch_is_bounded(self):
        s = snapshot()
        s['apps'] = [app('test-' + str(i), 'Error', 'OutOfSync') for i in range(10)]
        self.assertEqual(len(self.state(s)['recover']), 3)


if __name__ == '__main__':
    unittest.main()
