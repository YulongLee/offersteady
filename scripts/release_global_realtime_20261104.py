"""Pinned Global performance/companion136 release; run only on Global host.

Default action is preflight. This controller calls no historical deployment
entrypoint. Private configuration snapshots and command diagnostics stay on the
server; output is fixed aggregate release evidence. No user work is terminated.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import time
from urllib.request import Request, urlopen

ROOT = Path('/opt/offersteady-global/releases/20261104-global-realtime-blocking-1')
RELEASE = '20261104-global-realtime-blocking-1'
PROJECT = 'offersteady-global'
_LOCAL_SUPPORT = Path(__file__).parent / 'release_support/global_realtime_20261104'
SUPPORT = _LOCAL_SUPPORT if _LOCAL_SUPPORT.is_dir() else Path(__file__).parent
BASES = {'backend': ('852d46d9a890ddb763f63167e9d4e67eeede06d12fc8a03bf59e88e9e5bd5cfb', 'sha256:c68c315beb7977cc88c4478d8b2464a560cf9a1226056492c9402d330d9a3398')}

# Exact historical stopped build container, independently matched against the
# October22 frozen non-target. Its existence is preserved; no lifecycle action
# for this container is authorized by this release.
LEGACY_STOPPED_NAME = 'zealous_bhaskara'
LEGACY_STOPPED_SIGNATURE = {
    'id': 'b26658773fe6a73626510cba0116d31bb3154d1fb554ca521deb254ef21ef57a',
    'image': 'sha256:414cfd1c18647de7db5857d6cadb64e46d7e8508c837e7d5e639a682800a3e47',
    'imageReference': 'sha256:414cfd1c18647de7db5857d6cadb64e46d7e8508c837e7d5e639a682800a3e47',
    'startedAt': '2026-09-07T09:39:55.330513404Z',
    'health': None, 'running': False, 'restartCount': 0,
    'configSha256': '0d694f0b69eaa0caa369fe2588e9d2ed89bbb17be2783f02cd3bb22f2efc24ea',
    'hostConfigSha256': '229cb2b629d3fd0630052e491427c9fd2382d6f4bc74fba1d1a66f4e3e952126',
    'mountsSha256': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945',
    'networkSettingsSha256': '141afbcf56bd0eb2fe360776ff29c34e173b5e3a300da1c994721fe9a068fddd',
    'networks': ['bridge'],
}
EXPECTED_NAMES = {PROJECT+'-'+name+'-1' for name in ('backend','web','material-worker','admin','analytics','postgres','redis')} | {LEGACY_STOPPED_NAME}
BACKEND_FILES = {
    'apps/backend/app/modules/web.py', 'apps/backend/app/services/document_service.py',
    'apps/backend/app/services/session_service.py', 'apps/backend/app/ports/interview_session.py',
    'apps/backend/app/services/interview_session_repository.py',
    'apps/backend/app/services/postgres_interview_session_repository.py',
    'apps/backend/app/services/realtime_speech_service.py', 'apps/backend/app/modules/screenshot_answer.py',
}
MANIFEST = 'apps/backend/app/global_desktop_release_manifest.json'
HISTORY = 'apps/backend/app/global_desktop_release_history.json'
NEXT_PATH = '/api/v1/screenshot-answer/desktop-devices/{device_id}/capture-requests/next'
FINANCIAL_ANCHOR_MS = 1792604406734  # original actual Backend start, never a candidate restart
GATES = ('legacy-gates/check-idle.py','legacy-gates/check-mock-idle.py','global_mock_companion_idle_gate.py',
         'extra_idle_gate.py','active_work_gate.py','resume_optimizer_idle_gate.py','global_financial_idle_gate.py')
TCP_GATE = 'backend_tcp_idle_gate.py'
TARGETS = {('macos','arm64'),('macos','x64'),('windows','x64')}
SHA = re.compile('[0-9a-f]{64}')
IMAGE = re.compile('sha256:[0-9a-f]{64}')


APPROVED_BACKEND = {'apps/backend/app/main.py': '1d61a2b10a5bc4572bbe676e40954419076cc08ee234fb354e61f1d28bae85cd', 'apps/backend/app/modules/realtime_speech.py': 'ec250621dd83a98b93a1ee72155dc083ad122344ef80bf9f79753495a3c16335', 'apps/backend/app/modules/session.py': '9d71143cdc330afa92bbfe353eba4c0b4165949e3b56cc739296c0855ea14d03', 'apps/backend/app/platform/cn_realtime_lifespan.py': '54b7709fb7a5dff7733cd48257bcd04e1cd789c49818d1d6bebb0b210393f42d', 'apps/backend/app/platform/cn_realtime_loop_monitor.py': 'b464a83bcc35744d80ef76cf6a2c2760df0590b207c85039c9ff6885ab5c61d5', 'apps/backend/app/services/cn_realtime_entity_state.py': '23a7ba15c30ac651a2859b1391ca563b8799f85f1e73145cc546d8833c7b8f05', 'apps/backend/app/services/cn_realtime_io_executor.py': 'da4b409736d1f2b4bee48442ec34037046797442ea65751fe738e756a489b8d2', 'apps/backend/app/services/knowledge_retrieval.py': '851b7bac82d6feee3ec4e37eda60bbbebd9b7c0c85489b7b77cd838d98a50e5b', 'apps/backend/app/services/postgres_material_persistence.py': '6bc75c3286d2bc9747c8178404818c6ec3b67681a0e3db5f02d457786d384601', 'apps/backend/app/services/realtime_speech_service.py': 'd87b760d4c5fef13e3670b2e1d3d0978c7fd829288632b39ae1af56c669530ca', 'apps/backend/app/services/redis_realtime_speech_repository.py': 'cf94a640779745788791bf3e3e18855b4713993497cccc7d442def91ea1d084c', 'apps/backend/app/services/session_service.py': '34280a60937b8755224ddc0fa1fe084ff6f6ffb9ee091a0c82700c7e49f4aa36'}
ADDED_PATHS = {'apps/backend/app/services/cn_realtime_entity_state.py', 'apps/backend/app/services/cn_realtime_io_executor.py', 'apps/backend/app/platform/cn_realtime_loop_monitor.py', 'apps/backend/app/platform/cn_realtime_lifespan.py'}
CANDIDATE_IMAGE = 'sha256:457a18eb4eec92857e76200f7a3139983a70838a01be66bde97f4d5d58650abf'
BASELINE_INVENTORY_SHA = '690dacc4612c34d2fa794e111f374e9f60dfd2602023279a5af90ad71abde4de'
RUNTIME_BEFORE = {'python': '3.13.16', 'dependencies': {'PyJWT': '2.15.1', 'aliyun-python-sdk-core': '2.16.1', 'aliyun-python-sdk-kms': '2.16.5', 'annotated-doc': '0.0.5', 'annotated-types': '0.8.0', 'anyio': '4.15.1', 'argon2-cffi': '25.1.0', 'argon2-cffi-bindings': '26.1.0', 'certifi': '2026.7.22', 'cffi': '2.1.1', 'charset-normalizer': '3.5.2', 'click': '8.5.0', 'crcmod': '1.7', 'cryptography': '50.0.2', 'fastapi': '0.143.0', 'h11': '0.16.0', 'httpcore': '1.0.9', 'httpx': '0.28.1', 'idna': '3.20', 'jmespath': '1.1.0', 'offersteady-backend': '0.1.0', 'opentelemetry-api': '1.45.1', 'oss2': '2.19.1', 'pillow': '12.3.0', 'pip': '26.2.1', 'psycopg': '3.3.6', 'psycopg-binary': '3.3.6', 'pycparser': '3.11', 'pycryptodome': '3.24.0', 'pydantic': '2.14.0', 'pydantic-settings': '2.15.0', 'pydantic_core': '2.50.0', 'python-dotenv': '1.2.4', 'python-multipart': '0.0.32', 'python-socks': '3.1.1', 'redis': '8.1.0', 'reportlab': '4.4.9', 'requests': '2.34.2', 'six': '1.17.0', 'starlette': '1.7.0', 'typing-inspection': '0.4.4', 'typing_extensions': '4.16.0', 'urllib3': '2.8.0', 'uvicorn': '0.54.0', 'websocket-client': '1.9.2', 'websockets': '17.2'}}
SCHEMA_SHA = '0d25024e9025059e373e63a257d652c809b2865a2ba3e2f31c1a125edc3cd097'
NON_TARGETS = {'offersteady-global-redis-1': {'id': '4a3e582ecc122e2c7711ab3524f7023f0315bb80c3777001c35a3cf529b92e17', 'image': 'sha256:ff02b58f971e7d7d156a1267e283fcbbeee91773b6aa36c49dac28ecfe28eadf', 'imageReference': 'redis:7.4-alpine', 'startedAt': '2026-09-04T05:48:44.636538598Z', 'health': 'healthy', 'running': True, 'restartCount': 0, 'configSha256': '1e9d86912c8bb0d8a3efe59d4c032e8cba29bde4c91b5131edaaa7501fe5dbfa', 'hostConfigSha256': '038f66f294167cc1b3e2130b5e12450102602b217d7f618dba3584cf38f55646', 'mountsSha256': '713b5b0f4af1b6a2a1271484c5a9a800bc1daa18ddbeb1bafbb3abbba0cfada6', 'networkSettingsSha256': '44f856350aee3e4fa3d181b9c7a3502ce2c81888581f8d2e2267cccb508cddd6', 'networks': ['offersteady-global_default']}, 'offersteady-global-postgres-1': {'id': '4076751a784b18127956e5be7fc1e4315f2d7918c815157a372bef7638670397', 'image': 'sha256:ccc6e83d6e35e931dc7c5def2022729d5a6c370318d099181995567ff1fb4d6b', 'imageReference': 'pgvector/pgvector:pg16', 'startedAt': '2026-09-16T18:57:12.9794071Z', 'health': 'healthy', 'running': True, 'restartCount': 0, 'configSha256': '08f8f7fe040fc03a5d93c96d403584890643a88afd04124ae92e06a84be7fa4a', 'hostConfigSha256': '95ac99d698232e91fde9ace0f2a4703db2b9b9c6b8ec21770f03492138c257d9', 'mountsSha256': '7bb2e6c39788b04dd63cf9a1fe32660a14d769a9d0d92db2c683eead1eb09bbc', 'networkSettingsSha256': 'c38b42e6c64b75e37b5ef287c25b3993c8423458cae42e880c0255e98a90e8c8', 'networks': ['offersteady-global_default']}, 'offersteady-global-material-worker-1': {'id': 'e6f68f5f182e73e831e7b9c0633d3a8edd46e2cc0c1d1badc2cedd09a2591fea', 'image': 'sha256:dc8a809fce79291d15a127f8121fe7f87a3d1f51b3d77422aba81c569115890d', 'imageReference': 'sha256:dc8a809fce79291d15a127f8121fe7f87a3d1f51b3d77422aba81c569115890d', 'startedAt': '2026-10-21T17:39:40.786285622Z', 'health': None, 'running': True, 'restartCount': 0, 'configSha256': '4da66307494b25ef2274acd2beb6cb09781bf316cfa63ef218be6c2d00c733d0', 'hostConfigSha256': '619183d7d45cbbd874579e040a768c22e7a4dbc0293399ef35daa0f16850c5fd', 'mountsSha256': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945', 'networkSettingsSha256': '7ffa0d551f48136c005010d6bd8703cff7678518f15434645ab4543d76a9063e', 'networks': ['offersteady-global_default']}, 'offersteady-global-analytics-1': {'id': '143b2916b9528c889b80d110319545e91150bce43241bd4abaddcf357e2b4785', 'image': 'sha256:698c7e1f13a011f3228d8062c3cc97d846eef7cb65b5c093a792385eeda3afcf', 'imageReference': 'offersteady-global-analytics', 'startedAt': '2026-09-21T20:07:42.456480969Z', 'health': None, 'running': True, 'restartCount': 0, 'configSha256': 'e436d8172b4b3bda2faa468243c7e7133ae9de7a9df4d3d45cb8cd6eb5073a6a', 'hostConfigSha256': '3d73d7e82cb6b4390aa2e812e2a8e6e48366c8dff99d5613edcb1d7e65da307c', 'mountsSha256': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945', 'networkSettingsSha256': '619afe2a448d4a34a98c865924ba63b715ec9d93f3126f5633f8a8677e976046', 'networks': ['offersteady-global_default']}, 'zealous_bhaskara': {'id': 'b26658773fe6a73626510cba0116d31bb3154d1fb554ca521deb254ef21ef57a', 'image': 'sha256:414cfd1c18647de7db5857d6cadb64e46d7e8508c837e7d5e639a682800a3e47', 'imageReference': 'sha256:414cfd1c18647de7db5857d6cadb64e46d7e8508c837e7d5e639a682800a3e47', 'startedAt': '2026-09-07T09:39:55.330513404Z', 'health': None, 'running': False, 'restartCount': 0, 'configSha256': '0d694f0b69eaa0caa369fe2588e9d2ed89bbb17be2783f02cd3bb22f2efc24ea', 'hostConfigSha256': '229cb2b629d3fd0630052e491427c9fd2382d6f4bc74fba1d1a66f4e3e952126', 'mountsSha256': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945', 'networkSettingsSha256': '141afbcf56bd0eb2fe360776ff29c34e173b5e3a300da1c994721fe9a068fddd', 'networks': ['bridge']}, 'offersteady-global-admin-1': {'id': '175d559cec8fd9b13306482b5438d387dce62bd94d78d0494623179e3850f0c4', 'image': 'sha256:c094f39b2a03ef69e7a864b1bc3c38d4aa06f98fa7640d805eea7e15498341c0', 'imageReference': 'offersteady-global-admin:reliability-20260929-2', 'startedAt': '2026-09-29T05:31:27.371255447Z', 'health': None, 'running': True, 'restartCount': 0, 'configSha256': '68772eca227c16a8dec4e68e8027b1d39bdaa1b173abf843cda6c38b64c8df70', 'hostConfigSha256': 'b068d26099b0f9c8cfdacd3e1163a5911061d408a82c83530846027033ca29df', 'mountsSha256': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945', 'networkSettingsSha256': 'a50a8d61e8dcaa5f16ab58311e0e3fb1fed54c67855b4a2076d9dc4c55071b67', 'networks': ['offersteady-global_default']}, 'offersteady-global-web-1': {'id': 'a164dbd6999dbfbb47969baee68b482fdc6c100a9c3b0d8f6fcadc9a3c2523ba', 'image': 'sha256:73c351fbc0502f50989b729174620173c80988292fe6d0d2b4fcf660f29caa44', 'imageReference': 'sha256:73c351fbc0502f50989b729174620173c80988292fe6d0d2b4fcf660f29caa44', 'startedAt': '2026-11-01T19:08:04.603972008Z', 'health': None, 'running': True, 'restartCount': 0, 'configSha256': 'a1013d705a036ce46ca01d847e2e84e07625abbfe4d34227338eabcd67c5083f', 'hostConfigSha256': '39b1ca778c16d96f953346b5333d234b6f24a882b9b6bc2b19e82009ea04f65d', 'mountsSha256': '4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945', 'networkSettingsSha256': 'd200673fec3a4e9fcdf790ad46860f4b3eb7acf61d5cb923a1fbe63e6e1d0d1a', 'networks': ['offersteady-global_default']}}
WEB_INVENTORY = {'index.html': '60c50c70d94b60eef620a5d02ef6fe19aa56313d5039fbfc5b60fadd22389ad9', '50x.html': '876766b4e80133fd490603e073d3567425b88794828a9292104244c9e40875ed', 'contact/index.html': '59cafbf4d550d0eb3b7848495a9dd9490e38359a4eccdd49cdbd0e5003060aab', 'contact/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'security/index.html': 'b04829d9d3caa451424398eaafe594f795b6bc8101f9d03987e753873603ec5d', 'security/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'download/index.html': '3f7dcfb6a5d00152ac1621b1983c1fd160376ace02635a6b565c12c14fccf3cd', 'download/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'about/index.html': 'd61b9c5d0008e37ba63ad3a7708d3db8bed82c21172ff1b7a83cd9bdf40d80f4', 'about/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'interview-questions/index.html': '8787a68a26fa68471355d14158793aacb889f76bb04c3599629f620b30bc06a7', 'interview-questions/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'features/index.html': '94dcf1b1e2be66edba5355956339b507402c852f5c2ef046eddec97909d4f658', 'features/realtime-interview/index.html': '73f966446542597095ae7b374e357988edb86a809458e7f3b19f665c8c4bb65f', 'features/realtime-interview/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'features/ai-interview-assistant/index.html': 'ec20f3b6a30d8ce4426a600c23e85bf6b40ceee5963904743cfeb231e4fbcb75', 'features/ai-interview-assistant/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'features/interview-review/index.html': '2bacdf3061a25947e29b9ac0fc1938324933fb27e816f8e38734ee382671631c', 'features/interview-review/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'features/screenshot-answer/index.html': 'c599067e171bc3a0ea2f4193e73f3f30b6a8a5934fd7ae23b2fde93c1309991c', 'features/screenshot-answer/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'features/._ai-interview-assistant': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'features/._realtime-interview': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'features/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'features/._screenshot-answer': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'features/._interview-review': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'terms/index.html': '835c5d58ca8b09c2f921457d744f7feda8e7a80874e7e30a5e08fab849899d5e', 'terms/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'offersteady-global-build.json': 'b99e0dc7a718e9fad750b0214198d5d2869ab7bd9664af09800b81613d89b72e', 'guides/index.html': 'de77d57dc7b1aacaa7b94d113e86d96d6f5702ad7457bcc9e3157e97898deac3', 'guides/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/preload-helper-NuCatGIt.js': '9dbebe8545cb7fba5ea976dac09317c7070ae18c80bdb523e73bc02921c5af0d', 'assets/assets.manifest.json': '81ede862cafa4f51ec99c4ed05cadee147593fc05d7422fcf3ba9c88558d9b96', 'assets/AnswerWorkspace-B-AXznAE.js': 'b78a1bfb9a4ffcdb476465f676d361e1381c18bfea0edc087f1b889358dd030b', 'assets/PublicReviewPage-CTonetRH.js': '1ea2860139228002ffc50f55d55e0e6e4551bf93dc8788e15c3aeee94e545874', 'assets/LegalPage-QErOMEEv.js': '91a590e79e2b2c416eab8db8048a0cd9d4db25b9c755860f653abfadb9ddc342', 'assets/src-CjIOFNFz.js': '7d588a1335231ec8e0ed4aa3f91a7dca2d23e8a0f7dfdefa04e9c94884e2ca9f', 'assets/dist-mhvK5xwY.js': 'e5140b829cef18e4cbc279688eb48a92b3647ca7d1f51490e8cfcb52a552ee38', 'assets/main-Crtr957i.css': 'a6e92b29eb79cb1c67aa5c988db044a34f87985355f773b7fd29e307989ea50d', 'assets/LibraryManager-BA22J9Gs.js': 'cc64d8f6cbfd1701aba8c9d779c11aa0d6926b78a98ba33eb908386e601443c2', 'assets/interview-review-word-export-DkKe9SVl.js': '9945369f0e602a26c67fc72cf919d8898b19f582f8dc9d8d7696ba71719f6a90', 'assets/DownloadCenter-BWBSRLFX.js': '28e7813797585a0a432428f8642736a3e99d18603a2c610e0b2aab0563fc8768', 'assets/GuidePage-BGbpj3Kp.js': 'ee7e5e49339db5cb538ed81d156d3944cb12f58dab28129e4d055d7e6baa43aa', 'assets/rolldown-runtime-aKtaBQYM.js': 'cb2fb01f2064eb36487466778d2ffc4c97ad86af89be1635209de18f0b5b2236', 'assets/auth-client-h-6-wio_.js': '6f428ee0079c6e13a64c25835a005bbd5fd7a2e24cc13ea33558fbbd33f42b26', 'assets/GlobalBillingPage-C8f-RSvy.js': '903ad044ad5ba13aaee925a0677f6f3690e94aa8d739d340ff49eff4d62766d6', 'assets/global-jsx-runtime-DwjihOEw.js': '89cfc99107fddbc7ec7eb7d19b67fd242c2f7a7f172c6f78b8fe40aa0d8d51f6', 'assets/main--KDK271G.js': 'de32e7392338089fdf81b24b7f9c1c7a5cc82a38358bd1977f515f9b73be2aef', 'assets/brand/favicon.png': 'd05ede3067dd27965ed4a572d5f7b4538385f68479c174c18ffb2a421605a686', 'assets/brand/app-icon-96.png': 'a60444614a351147c173fd2686b6eaf9eeb0a1297747c787cfb3bdb1b8967a85', 'assets/brand/share-card.svg': '9a9cc4ff7ef63bc6361328cd4e53ddeac89f3d224c5732a1a7b4cdf8e894c9a4', 'assets/brand/app-icon.png': '4937f4ef85235137a03d99ba1cac80ee43ebd2fdbc57ee8a383001be6912f66f', 'assets/brand/share-card.png': '640ccd3e8231e820b66dff9baaa90e0c5294869673c27e94e1489f61c7c06917', 'assets/brand/._app-icon.png': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/brand/._app-icon-96.png': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/brand/._favicon.png': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/brand/._share-card.png': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/brand/._share-card.svg': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/LibraryManager-ad484874-c3d99478.js': 'bd2e91d8e44ac034e8416df9f936de0770d39273002256636c1e7f27ce0d0dfc', 'assets/main-08d5d48b-1eebe5e2.js': '3b669f768fb8fbad8ff20aa35e65beb9410679179dbba17b89218fd6374bef71', 'assets/WorkspaceApp-6c6d97a4-b2deeab9.js': '5ad0e417d93d016b33c7a955d7f747e3dda774a66c6acde80b5cac3b4191957a', 'assets/GuidePage-25faf907-6c620bad.js': '619dc5b69468c58419db3f1d8f46e3ec25f17d693df44e5a4e06210859ceee3c', 'assets/product-edition-255ce93b-e5dfdf26.js': 'e463f1ff1112f66a68e11c798cab560b9077f2653b7f2148d485bfa5a4673e61', 'assets/WrittenMultiScreen-532fb063-b439161c.js': 'b57656406880ce9c295904c67e7f4f78cacb7015cf9c60880c093510b676c609', 'assets/DownloadCenter-4f4b7a2d-c73921a6.js': 'bead6812c9735b46b57a92316653052d720cc8a5f0b09c61a9a8846d199a83e6', 'assets/live-workspace-fd94029f-b33e76a6.js': '7cd0ff91a824368c045b3f2074c44a0338fee38d10b096d55b2d1bab5d802b10', 'assets/LegalPage-f04fd293-1aafb4b8.js': '25597f916ad33c4612b1fa1d2a03766ab00fab4605d71d986620f3bbed3c882c', 'assets/ResumeOptimizerPage-515d5969-3bef685c.js': '21d8beeb9082c6500eb9465e6ab11c08b14f09c62fe9417d0411cf73963f446d', 'assets/AnswerWorkspace-c316f286-51a974b8.js': 'e931eea040a3c357d1490dd95119a068b733b50ed113183f0c9bd63fcc6b7637', 'assets/app-adapter-59d370b8-9e3afa1f.js': '95d8e93b2b2138ce093701a0cb202f2011a67539699c82b0e236bf0d31b50d8a', 'assets/GlobalBillingPage-ea67912f-f9a7f66f.js': '195dbf736b6da5199cfdfa23d07d34345bd3a4a4e10a78313a5b9bc92a397621', 'assets/MockInterviewPage-5c89cff3-eb3c70c6.js': 'de8230a58a96219f503a3e9c22729174b555a7ec24bbc954cf644da29158f27f', 'assets/PublicReviewPage-b9018c97-c6a13656.js': '940b2642f92df03b6eaa6b7af55d984d1b871a302e90d3dbb8489faf0f30f8fb', 'assets/LoginPage-1cfc184f-14ed4ae4.js': 'b9b50beadcb710ef6e29cc42f2539976a83f3784afc1fff76e01f26ae4f361c9', 'assets/GuidePage-25faf907.js': '249d0ba069188b5d2692ab72d586a169f8e4471f09caa51c610bab2914651212', 'assets/LibraryManager-ad484874.js': 'dccec0a21a7bf613914ce8a45e4190aeda426c67e26ba1b53a7c332219020bbc', 'assets/PublicReviewPage-b9018c97.js': 'bde6427667c71a8e9b8754f68f5ce8170160b9f8a0547ee87fb0210b3f8a5117', 'assets/written-multi-screen-adapter-90a5ca35.js': '90a5ca3517805241e30333820e4d989457b6b8e35631c68dc5f95dd2cae39ff8', 'assets/product-edition-255ce93b.js': '7244454aa164dc4dd9cd56d63abf0c56c8da1aaf4bbb651c3a952d8c6b7ea77d', 'assets/live-workspace-fd94029f.js': 'c771b2b6b724650dc3816d85491ea6d25529cc1213ffab4cd221459199dde0a1', 'assets/ResumeOptimizerPage-515d5969.js': 'aa09aa65ab9157ac6719425461fe1e2c94fc831d7ec0fbae64fd9f2bd60bc14d', 'assets/MockInterviewPage-5c89cff3.js': '1bf31a9c89e0358230d99050f690b87165475c37eceff372894c387847917f8f', 'assets/LegalPage-f04fd293.js': 'ed74f8fb763ac799c9c2fa03a6fd25f64d690d00953872ca0af66f2e9f41b0f2', 'assets/WorkspaceApp-6c6d97a4.js': 'c9db5b293c296580fa1a6563552ce8587134b8bd52264e15ebfe014328cb3b77', 'assets/GlobalBillingPage-ea67912f.js': '5a9a96f1069b51628b01a4cbf1e6427f7c1de237376c77fd7375208f2d457677', 'assets/WrittenMultiScreen-532fb063.js': '44842ceb776169832e52dceca733908efbf8ce656eb1f639a4c76cccff83b946', 'assets/written-multi-screen-093353eb.css': '093353eb173d62ea32359cf64be89875db357f5ef5796a352e8daa6f10dbd825', 'assets/app-adapter-59d370b8.js': '7819af922b39f908584a5c7a5cb4c3f75f2b8385201bf58aa32dee9a2220aad7', 'assets/LoginPage-1cfc184f.js': 'c26bf1db0cbb20f9b65c5afb9500335614d46d0cfa27de0d24b04a95f11d2946', 'assets/AnswerWorkspace-c316f286.js': '0f9eb7900e642a020180e97a5b0a7c0b68bbd120a491476f860c1500d571671f', 'assets/DownloadCenter-4f4b7a2d.js': '7fa962726b96afc27729697ec9f2c08402a91fbadcefa2c6469874c97dfc9c68', 'assets/main-08d5d48b.js': '137ddf68a7c05c53db11ace3cf02512ebe08f7dd7b8a7a29be3603c5fdb1ef94', 'assets/WorkspaceApp-CIvsP91G.css': 'dafa3179047c89b066907f2bdb915f36efa869d159c327f80c34e9ab9c502ec3', 'assets/ResumeOptimizerPage-Cw7Wjymm.css': '34daaa7fb25e516116b6106102c7d44790278fc29f9488533a3ec07ed849835d', 'assets/live-workspace-snPJWij9.js': 'c1a6e3f2214b4cb43c8bcfb02c43c92c80710da87b59f476d6740322a6dc1000', 'assets/MockInterviewPage-Df2hZMmA.css': '8d3c6b169831051d57edae421b3bc16e536713373b6dda57fc086d1ff0c278f1', 'assets/MockInterviewPage-C3Axvpht.js': '155eec141b090be7fdc6f5d0566b81875337bc0d212fba04f349a15cd073f968', 'assets/global-jsx-runtime-pOLjH0Mm.js': '1dd3ede4f20f6b78ad7238e75141138cacf3deec404743f194742832c2c7af47', 'assets/DownloadCenter-D10Ki_HL.js': 'd5074054aa0f6c0851f20286b19700b5cf6534e701a49a714530c24ab4a3ec61', 'assets/GuidePage-BZKq5M1n.js': 'a9308e7cb27ee7db916c9cf64dab523c698af55ff15da23f940ade57a22a6265', 'assets/main-XGzCeNsy.css': '9eb380ab9ba82892b62eee5aff46b1e475a81e8b06c6838d2fdf8705af0bfa43', 'assets/mock-interview-word-export-DKLLtJZl.js': '90bbdab2783a07c4d3b6fc6db94e69a67a443eb1a4ad5d1ffa9086be30d76863', 'assets/ResumeOptimizerPage-Ca-z8Ne1.js': '153ef7b338d5354506437c636ab998d896b9374b09dcbf065695d06faeeb7b97', 'assets/mock-interview-report-CdRyItqy.js': 'b3898d3c45b9334a794c987c2c87bf2373e49672d26ae9decfdb39bd6e78882d', 'assets/AnswerWorkspace-qoke4tde.js': 'f61aa335a52b5d4bbb4ae12c2f10fdb28261525fae428542dc2f0d66d34e234b', 'assets/library-processing-polling-DC98OrqS.js': 'f12c271bb50f5bb659dfc9b88a38e9dc088f22138ee1cae7fa1c29022b4dbc8e', 'assets/main-BsudckLO.js': 'fd53aeac82aefee9d68ed56b447087cf058d3687702be07eac9fb20dcfe0afe0', 'assets/GlobalBillingPage-g3GW237y.js': 'c5753687eb720dc3f8ff08842c6c836679f2991fe66ac928d09a3ad615c2d0a9', 'assets/WorkspaceApp-Cx3BEHut.js': '4791636a4e2205cd2ced512224a913c4b3dac1d6d3b55773df5c46ed5abbfc57', 'assets/product-edition-BAS44ZiR.js': '286b7bbdd25bd0e46e90427a13cd2541e99b59d883fc431b0fab1f49cf850efc', 'assets/platform-P6gWzGSM.js': 'd6624d5091fae360fed778d64b423371366b92fe9902cee350901090c68ad643', 'assets/LegalPage-C7If_YWK.js': '6f0123081c571d51c65b9536e5f36cfc4642cbb3ec39e1662dd6901a5aa6b7c1', 'assets/IconBase.es-Df56CME9.js': '76b35c3d25f8bbbb7535a85c9d68ff70314d195ca9bd3f41827b683e7bbe393b', 'assets/app-adapter-pNNZ4HU7.js': 'daa2dd66ee088b2bf93c984e412acdeead6d859dc8ce0023069ab187c12a037d', 'assets/LoginPage-BQBm65dp.js': 'a8c9454a33f8c016fffbd552d8900c68a5f0acd9cc60ce90f2b8d17f244125b1', 'assets/mock-interview/interviewer-v1.png': 'eef23f2f51ea176865e18862b1ecad2831f438b1c84faa3a6fb5ab9d881d8e32', 'assets/mock-interview/._interviewer-v1.png': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/LibraryManager-ToiYGxw5.js': 'abf974a07cb7bd436bc1ec5261f3858401b0d3dc14ce7c1775dfe1b02c772909', 'assets/PublicReviewPage-BbRf2UkN.js': 'f9422df337de6bdc5801109ec0dd9859793ee5f676be78f21eec2ce063a34f00', 'assets/WorkspaceApp-b588c31a.js': '1e7d4a4a900927c71b502c722ec83f3cfe669c47d06821ad3e7c387e21d1a5f7', 'assets/product-edition-8b060d5f.js': '1b15a116390225d265c6861b091002f97130dae20c85113fd0e0eeeea79725ae', 'assets/AnswerWorkspace-e6d12910.js': '35698eb32f60d7a1098b237974bd2bdd5d33f79fd7a669519b8ebf1609b3c4be', 'assets/PublicReviewPage-388a1e93.js': '0555d60bc27dd35ab2ba0c04f723da44be3f78ce37d844f4b40f87591250879a', 'assets/LegalPage-0402d05c.js': '3e9f2f8c88980ac56dc368bc73abbf410a00a67e7aa1d318d6fd52a4512b99b8', 'assets/live-workspace-ea5a1364.js': '3de1b186e40973850726cf24980195ce330ed933d84b898571ebed6204780e9b', 'assets/GuidePage-2c662f3c.js': '3d460d5c03d60751d270c79d8744ba3a8ed649a3f8cc6da1a76ba3bc1af9bcf5', 'assets/LoginPage-22649364.js': '139baacd67c9a4a512412d4cb6e1a79c79b9f43d866c7b9594b52f26291f2c37', 'assets/MockInterviewPage-c4ea13c6.js': 'c4973a61211366c57dda60cb25095857764e48b27ac2bdc0e5af42b4d8a007eb', 'assets/main-827d17f5.js': 'eb8c0b1073df6d429ceed334cec90f8d064acc16db92fb5a51b0c121678ed18d', 'assets/GlobalBillingPage-49c644eb.js': '5274720337570bf8c01df090d8e478aaf21dd1d3b2de6dba0ad8aea792ef2cb5', 'assets/LibraryManager-dcb38e04.js': '729c0c83bc94549deac9a642c2214261eece7d1cbedc91e35228a73558e20506', 'assets/global-state-coordinator-b58e7fb0.js': 'b58e7fb0c7c3bba53954ed66329d88b86c3916396dd7cae72f79e6c5e68388b3', 'assets/DownloadCenter-e219bf01.js': 'd4a230185854ddc69a293c9692960b1b1ffaef771a6a603bb0f772cf2757282e', 'assets/._preload-helper-NuCatGIt.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._support': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/LoginPage-CJc2Yl8_.js': '4bd2b38140923552def4edc6cc195d9a4f9a7eb1a3f6465f8429bc73b9a36c77', 'assets/._mock-interview': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/WorkspaceApp-Dbdny98S.js': '1a37b6e45d2d0bccaf51a151e69836117999d7947df4003d22d223cc45d4475d', 'assets/._DownloadCenter-z-QGjRA7.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._mock-interview-word-export-DKLLtJZl.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._LegalPage-Dkz1dD3c.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._rolldown-runtime-aKtaBQYM.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._payments': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._PublicReviewPage-BgERT42i.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._global-jsx-runtime-pOLjH0Mm.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/PublicReviewPage-BgERT42i.js': '2cd0346960eddec1b68a7e503ecf73c71d656866dbd8bae9224ffab840b022a2', 'assets/._mock-interview-report-CdRyItqy.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._brand': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/GlobalBillingPage-CwYfOdp8.js': '1e09e97691beb1addc37a5c5222cb897d3a2a906fba0954cb77ec0290b3eb90b', 'assets/._LibraryManager-DC01TmEE.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._MockInterviewPage-DQy7w99h.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/GuidePage-BihJLNRn.js': '2b8e553e94b129aea104802698d410696506053a0318ab922e4b5d2cf132ac61', 'assets/._dist-mhvK5xwY.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._product-edition-CCSMnxKJ.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._GlobalBillingPage-CwYfOdp8.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._MockInterviewPage-Df2hZMmA.css': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/LegalPage-Dkz1dD3c.js': '1c7fdcdc6f0cb62955ee782345a24014579fb27e41a638f212f050c3e639c67a', 'assets/main-g1kziTNb.js': 'fa6ac2f2f7bf67221c275eea7f00238629f4c6bb9fa885d23ee937dfdb49d2f3', 'assets/live-workspace-DdAFzDj5.js': '7cad6162af5d029a383bb95e9ef32b7cb75ba1ba6d55b54559c0d831b251bfe5', 'assets/._IconBase.es-Df56CME9.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._main-g1kziTNb.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/LibraryManager-DC01TmEE.js': '8a7bdd3e11a09a2f1b96783710f0819a671046fb60ae620b5a2ca44a202d0990', 'assets/._live-workspace-DdAFzDj5.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/DownloadCenter-z-QGjRA7.js': '12924f3cdbcaca6b2eab20ae04d582a1c3bcabef15722b44a618bece2ba434d6', 'assets/AnswerWorkspace-C_M2f7a_.js': '47ad6b6f601b6f074efc326142c386eff4ddc28362407fb2733b0b5f9380a3c5', 'assets/._interview-review-word-export-DkKe9SVl.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/product-edition-CCSMnxKJ.js': 'dcea4dbac2181dede1552469bec8a00be9a9e6041b82232da6de26c7d0afa7b3', 'assets/._GuidePage-BihJLNRn.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._WorkspaceApp-CIvsP91G.css': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._main-XGzCeNsy.css': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/MockInterviewPage-DQy7w99h.js': 'fd20b42b87c314265ea5238d520276d506a2b6f8af2fb85a290391618a5805d6', 'assets/._AnswerWorkspace-C_M2f7a_.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._LoginPage-CJc2Yl8_.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._assets.manifest.json': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._platform-P6gWzGSM.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/._WorkspaceApp-Dbdny98S.js': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'assets/DownloadCenter-nOmNAL4A.js': 'eb82eaa26a67ac7bfe77cc577329006542dd15811688d09cce32ea0034789919', 'assets/AnswerWorkspace-3DWNLiLq.js': 'be3d0a86f6d8992b88ab866a9e396e805a19f0eb3b7c54f942d89b38fc321b04', 'assets/GuidePage-Doiy1sCs.js': '3c52dcc138ba967f7a21e8edae4209c62e3839c5849c701b3d6427bc0a8abc63', 'assets/LegalPage-fCv9g-R0.js': '0a8543a6753fd9fdb8edf783f4b2d6320f9b1129a4dde5295a9d4477bb49b828', 'assets/auth-client-1xE3Y7-x.js': '2bbf3f6f7bc275b3e5c5c47a17264e8865df682398da8521f3b5a8ea76332b37', 'assets/main-BNYnTaPI.css': '04ea147b9365c9f7c7dd6a6ee6bebdda13b4fe96f349a0b5453e09e0ae5baf02', 'assets/main-_8WpUbcl.js': '3a12bf5aefbb796278b5647a6ba39a6dda812f20d95f0121f4c86b3800c3e943', 'assets/global-jsx-runtime-NxP3PwHg.js': '743148439b165e9809be518471a476d0c0dcee2baf5a3ad33db8e092ae09b34d', 'assets/LibraryManager-2IGFdYU3.js': '2262c5851b5588c415efbeae1450ee5e9cd0ee8ebc762c20f152bb117165135c', 'assets/GlobalBillingPage-z9iv2ONu.js': '06e01f945d227cec6ddd83eeed588e92f785175892bfc98b9615da3487c7d6ca', 'assets/PublicReviewPage-BXM7q0Zi.js': '4853dc57b7684979a226979ba5893405b78df68447dc3caf9f89f806f3f25c3b', 'assets/MockInterviewPage-CF2VULJq.js': 'd35560615d51df887453f5e9e1788862e685a1a5b657234ecd1b99f3c6f1bf75', 'assets/LegalPage-NHuIMXck.js': '405971892522d9efdabe4eca4eb7067eb767246deb4a8c50ed63fd12d05321e5', 'assets/PublicReviewPage-B9GbNCvY.js': '7788e8425b7b7198e1df123a593c89d4be23e626297928d8865dab05ba611144', 'assets/LibraryManager-DTxai2vv.js': 'a10c067a76a9f320e7d91b722c6d066de140856d0db3bd54bae8620d260cf220', 'assets/GuidePage-BW_uhY5y.js': '28ef770147b9dd59cc0d1991ff2692dddf703a095e550dd157c87799613a476f', 'assets/auth-client-DkYBckQl.js': '1d1ee028ea763b865df0dc88a1734555e6c78423c04a4249941cb11054dbdc7d', 'assets/GlobalBillingPage-MwMAWivT.js': 'cdce7b87cbfb4d18093cceb6ecd508dc2cc648cf82e289685dfdf16619528f03', 'assets/DownloadCenter-Bn9hdYPI.js': '46938586eeb4f100fbc5e3233673cafcc7a7b48c0fb0fee586cd461b0d24df8a', 'assets/main-UMAFg5wb.js': '0e49f0ddb40f6c33b7dfdab78621ab9d0aa414bc4bdb990f93b3a832a40325ef', 'assets/AnswerWorkspace-C_IR-QnP.js': '40bfcb20f17e1b8043914e9cf4bf16405b6cb5ae6f5ecfb22b046480dadce338', 'assets/LibraryManager-COhCJZim.js': '848b4b277e3822534ffc79eb8169ff82c3272f7e46f0e329029ebe1e278250a9', 'assets/AnswerWorkspace-ipgDk8kn.js': '22868f042e3b5461fbfa841c9f06c75334ddf4c3bfd293303b6d7eb5cf770740', 'assets/auth-client-DRcc6xLh.js': '969629276fc1616d0843a2dc4601e5a98d1bc6b19b74e51bd3490a5110764046', 'assets/DownloadCenter-B1k3sxWr.js': 'f759db46ba460dae64356ddafb5d85b10aa954d23130d3b2ca24366733df7a87', 'assets/main-SHx6gMHK.js': '51785240fcb486e18db6c29fba4140627818b83bbdc7da31cacce7abe27288d0', 'assets/LegalPage-BF0Khspo.js': '7d1ca6e054d0adcad7517c8de455c555b50bcde32ea37efb5f61207f449d231e', 'assets/GuidePage-CblCEGmp.js': '866f9dbcdcf51f64b9632ac2298ccdd1b988307bf18b2593e3b229a9dbfa0a00', 'assets/PublicReviewPage-D-R_wqF3.js': '2f8b70972165812856f5fa8e2cedc2c977a30177ede548e0d80b4b31a407a789', 'assets/GlobalBillingPage-DgBCCuR2.js': '33e7f00d832984302f31c346c48633ea612d4511681b69cf356212d6f3b19361', 'privacy/index.html': 'a50f3bb1a24455e7ccca849e74f3885586847607e01a01bfa5a7e09d57c255f5', 'privacy/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'pricing/index.html': 'c757a0e77d925bfaac126a19e0c8aa9d177f4168a48481e671486e82ef1566fd', 'pricing/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'refund-policy/index.html': '0c2d87db2f770e4314c0393336f71fb8bdc46ffdf4fd85f4f833403c7b4ca33b', 'refund-policy/._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'media/offersteady-global-commercial-poster-20260907.jpg': 'c6c41973a588081e3bcd01ea3c34623fdd62d73b017f2071b007a86e00200f78', 'media/offersteady-global-usage-20260907.mp4': '6a7c4cd444b383ee1d88d70e4920bde0c4abf33b1290ca05554b7a7560193dd2', 'media/offersteady-global-commercial-20260907.mp4': '42cb09a287ad460ee0f165320e30b69a28fb8d408afcc23f4d067ebea06d656d', 'media/offersteady-global-usage-poster-20260907.jpg': '7b7c8101805be7bacd4fb8afa27a98a532e662bd75a91208191a00f1e98f39b5', 'media/._offersteady-global-commercial-20260907.mp4': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'media/._offersteady-global-usage-20260907.mp4': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'media/._offersteady-global-commercial-poster-20260907.jpg': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'media/._offersteady-global-usage-poster-20260907.jpg': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'llms-full.txt': '6655a49ed4e880720e5f69749a4fe931fbd2be81fa1ce9ff9421094a81d03834', 'robots.txt': '3991f42ca1c3ab05ddb0fc4117312a0d7ed44f294644645dc1565414c7836828', '404.html': 'd27f43f49f9733bb29dd1a38164f6d16410b0d21bbece204ed66f741e657db3b', 'public-facts.json': '731ab64a3c60e01aaed9c591454c16c5dbc903c6c96705f8e68c3c9e24cb9326', 'llms.txt': 'c54ffd914f6338d421fe4d53752804331ee45f9c57d4e9036a17765a3f3ded8f', 'sitemap.xml': 'eb38e151a8f507f2ffca54f54fe2e86d0b34287906ee3d393e771d6710196195', '.vite/manifest.json': '6423de40173c8d2abc3770fa18b37cd8721443f441808f386e423de30e00c920', '.vite/._manifest.json': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._refund-policy': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._guides': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._seo': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._download': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._terms': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._features': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._404.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._about': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._pricing': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._index.html': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._.vite': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._media': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._privacy': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._contact': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._sitemap.xml': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._offersteady-global-build.json': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._llms-full.txt': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._interview-questions': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._llms.txt': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._robots.txt': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._assets': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._public-facts.json': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', '._security': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530'}
NGINX_INPUTS = {'offersteady-global-web-1': {'/etc/nginx/nginx.conf': 'sha256:4dee6b0c7c8278f6a9b827261c25d3215c9ea8955e41ff7fe3eabdd5297edce7', '/etc/nginx/fastcgi.conf': 'sha256:b2c3d480a58f61f3a7dc61850b461e892e36f236317765a4f2f6d558c928fa57', '/etc/nginx/conf.d/default.conf': 'sha256:94d545108b46ee806a392da0bdb4b36a55e2a0742a5568516eddc20c447ee304', '/etc/nginx/scgi_params': 'sha256:f27b2027c571ccafcfb0fbb3f54d7aeee11a984e3a0f5a1fdf14629030fc9011', '/etc/nginx/mime.types': 'sha256:6f95d1d7d75e3c072907d845622a69d23110d1266c16ff122b3109b8b21f3ae9', '/etc/nginx/fastcgi_params': 'sha256:f37852d0113de30fa6bfc3d9b180ef99383c06739530dd482a8538503afd5a58', '/etc/nginx/uwsgi_params': 'sha256:015cb581c2eb84b1a1ac9b575521d5881f791f632bfa62f34b26ba97d70c0d4f', '/etc/nginx/modules': 'link:/usr/lib/nginx/modules', '/docker-entrypoint.sh': 'sha256:3372fd90162da30d09f62c245e9c6bfd620fb0bb5b48ab54b16e804c2b9e8aae', '/docker-entrypoint.d/30-tune-worker-processes.sh': 'sha256:1f068aa49da8df46bfd5a917debf110af9b115370739e3be34af83ebf583fbce', '/docker-entrypoint.d/20-envsubst-on-templates.sh': 'sha256:253c8724acff9f5c0d0e8938e71fe7c33097d40031a5bc9c7f59dfd2ba5f1377', '/docker-entrypoint.d/15-local-resolvers.envsh': 'sha256:329a1e89cc898599338874f679e22711c4c2d69f65f98b64a72d8b708e69ee44', '/docker-entrypoint.d/10-listen-on-ipv6-by-default.sh': 'sha256:8c5d2c912416126c7d65651600b166c00ad9ca3e3af82487ddd5a5da94fb8fb5'}, 'offersteady-global-admin-1': {'/etc/nginx/nginx.conf': 'sha256:4dee6b0c7c8278f6a9b827261c25d3215c9ea8955e41ff7fe3eabdd5297edce7', '/etc/nginx/fastcgi.conf': 'sha256:b2c3d480a58f61f3a7dc61850b461e892e36f236317765a4f2f6d558c928fa57', '/etc/nginx/conf.d/default.conf': 'sha256:b9e0f1fb5417902352df69af518fe4c9454faac8042cb2e85786bef8772c8167', '/etc/nginx/scgi_params': 'sha256:f27b2027c571ccafcfb0fbb3f54d7aeee11a984e3a0f5a1fdf14629030fc9011', '/etc/nginx/mime.types': 'sha256:6f95d1d7d75e3c072907d845622a69d23110d1266c16ff122b3109b8b21f3ae9', '/etc/nginx/fastcgi_params': 'sha256:f37852d0113de30fa6bfc3d9b180ef99383c06739530dd482a8538503afd5a58', '/etc/nginx/uwsgi_params': 'sha256:015cb581c2eb84b1a1ac9b575521d5881f791f632bfa62f34b26ba97d70c0d4f', '/etc/nginx/modules': 'link:/usr/lib/nginx/modules', '/docker-entrypoint.sh': 'sha256:3372fd90162da30d09f62c245e9c6bfd620fb0bb5b48ab54b16e804c2b9e8aae', '/docker-entrypoint.d/30-tune-worker-processes.sh': 'sha256:1f068aa49da8df46bfd5a917debf110af9b115370739e3be34af83ebf583fbce', '/docker-entrypoint.d/20-envsubst-on-templates.sh': 'sha256:253c8724acff9f5c0d0e8938e71fe7c33097d40031a5bc9c7f59dfd2ba5f1377', '/docker-entrypoint.d/15-local-resolvers.envsh': 'sha256:329a1e89cc898599338874f679e22711c4c2d69f65f98b64a72d8b708e69ee44', '/docker-entrypoint.d/10-listen-on-ipv6-by-default.sh': 'sha256:8c5d2c912416126c7d65651600b166c00ad9ca3e3af82487ddd5a5da94fb8fb5'}}
PUBLIC_ROUTES = {'/': 'index.html', '/about': 'about/index.html', '/assets/AnswerWorkspace-c316f286-51a974b8.js': 'assets/AnswerWorkspace-c316f286-51a974b8.js', '/assets/DownloadCenter-4f4b7a2d-c73921a6.js': 'assets/DownloadCenter-4f4b7a2d-c73921a6.js', '/assets/GlobalBillingPage-ea67912f-f9a7f66f.js': 'assets/GlobalBillingPage-ea67912f-f9a7f66f.js', '/assets/GuidePage-25faf907-6c620bad.js': 'assets/GuidePage-25faf907-6c620bad.js', '/assets/LegalPage-f04fd293-1aafb4b8.js': 'assets/LegalPage-f04fd293-1aafb4b8.js', '/assets/LibraryManager-ad484874-c3d99478.js': 'assets/LibraryManager-ad484874-c3d99478.js', '/assets/LoginPage-1cfc184f-14ed4ae4.js': 'assets/LoginPage-1cfc184f-14ed4ae4.js', '/assets/MockInterviewPage-5c89cff3-eb3c70c6.js': 'assets/MockInterviewPage-5c89cff3-eb3c70c6.js', '/assets/PublicReviewPage-b9018c97-c6a13656.js': 'assets/PublicReviewPage-b9018c97-c6a13656.js', '/assets/ResumeOptimizerPage-515d5969-3bef685c.js': 'assets/ResumeOptimizerPage-515d5969-3bef685c.js', '/assets/WorkspaceApp-6c6d97a4-b2deeab9.js': 'assets/WorkspaceApp-6c6d97a4-b2deeab9.js', '/assets/WrittenMultiScreen-532fb063-b439161c.js': 'assets/WrittenMultiScreen-532fb063-b439161c.js', '/assets/app-adapter-59d370b8-9e3afa1f.js': 'assets/app-adapter-59d370b8-9e3afa1f.js', '/assets/live-workspace-fd94029f-b33e76a6.js': 'assets/live-workspace-fd94029f-b33e76a6.js', '/assets/main-08d5d48b-1eebe5e2.js': 'assets/main-08d5d48b-1eebe5e2.js', '/assets/product-edition-255ce93b-e5dfdf26.js': 'assets/product-edition-255ce93b-e5dfdf26.js', '/contact': 'contact/index.html', '/download': 'download/index.html', '/features': 'features/index.html', '/features/ai-interview-assistant': 'features/ai-interview-assistant/index.html', '/features/interview-review': 'features/interview-review/index.html', '/features/realtime-interview': 'features/realtime-interview/index.html', '/features/screenshot-answer': 'features/screenshot-answer/index.html', '/guides': 'guides/index.html', '/interview-questions': 'interview-questions/index.html', '/login': 'index.html', '/offersteady-global-build.json': 'offersteady-global-build.json', '/pricing': 'pricing/index.html', '/privacy': 'privacy/index.html', '/refund-policy': 'refund-policy/index.html', '/security': 'security/index.html', '/terms': 'terms/index.html'}
ANCILLARY_INPUTS = {'packages/protocol/src/material-upload-formats.json': 'e6607164d21950319ab2b6179d38ed6cf771715a2663c18db704af612907ac2f'}


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


H = load_module(SUPPORT/'base_helpers.py', 'global_perf136_helpers')
P = load_module(SUPPORT/'ownership_primitives.py', 'global_perf136_ownership')
GuardError, require, digest, canonical = H.GuardError, H.require, H.digest, H.canonical
run, inspect, environment, read_json = H.run, H.inspect, H.environment, H.read_json
write_json = P.atomic_write_json


def save(name, value):
    write_json(ROOT/name, value)


def emit(**value):
    print(json.dumps(value, separators=(',',':')), flush=True)


def bind_primitives():
    H.ROOT, H.PROJECT, H.write_json = ROOT, PROJECT, write_json
    values = dict(ROOT=ROOT,SUPPORT=SUPPORT,PROJECT=PROJECT,BASES=BASES,H=H,GuardError=GuardError,
                  require=require,digest=digest,canonical=canonical,run=run,inspect=inspect,
                  environment=environment,read_json=read_json,save=save,GATES=GATES,TCP_GATE=TCP_GATE,
                  expected_environment=lambda before, service, kind: dict(environment(before)),
                  targets_owned=targets_owned,gate_command=gate_command)
    for name,value in values.items():
        setattr(P,name,value)


def relative_file(value):
    require(isinstance(value,str) and value and str(PurePosixPath(value))==value
            and not PurePosixPath(value).is_absolute() and '..' not in PurePosixPath(value).parts,
            'invalid_release_relative_path')
    p=ROOT/value
    require(p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(ROOT.resolve()), 'release_input_file_missing_or_linked')
    return p


def valid_inventory(value):
    require(isinstance(value,dict) and value, 'inventory_missing')
    for name,checksum in value.items():
        require(isinstance(name,str) and str(PurePosixPath(name))==name and not PurePosixPath(name).is_absolute()
                and '..' not in PurePosixPath(name).parts and isinstance(checksum,str) and SHA.fullmatch(checksum), 'invalid_inventory_entry')


def check_schema_delta(before, after):
    stripped=deepcopy(after)
    try:
        old=before['paths'][NEXT_PATH]['get'].get('parameters',[])
        new=stripped['paths'][NEXT_PATH]['get']['parameters']
        extra=[p for p in new if p.get('in')=='query' and p.get('name') in {'sessionId','requestId'}]
        require(len(extra)==2 and {p['name'] for p in extra}=={'sessionId','requestId'}
                and all(p.get('required') is False for p in extra), 'optional_query_contract_changed')
        require(not any(p.get('name') in {'sessionId','requestId'} and p.get('in')=='query' for p in old), 'query_already_in_baseline')
        stripped['paths'][NEXT_PATH]['get']['parameters']=[p for p in new if p not in extra]
        require(stripped==before, 'api_contract_changed_outside_optional_queries')
    except (KeyError,TypeError):
        raise GuardError('optional_query_contract_missing') from None


def validate_manifest(payload, proofs):
    require(isinstance(payload,dict) and payload.get('version')==1 and type(payload.get('generatedAtMs')) is int
            and payload['generatedAtMs']>0 and isinstance(payload.get('entries'),list) and len(payload['entries'])==3,
            'global_manifest_incomplete')
    require(isinstance(proofs,list) and len(proofs)==3, 'object_readback_proofs_missing')
    seen=set()
    for entry in payload['entries']:
        target=(entry.get('platform'),entry.get('architecture'))
        require(all(isinstance(x,str) for x in target) and target in TARGETS and target not in seen, 'global_manifest_targets_invalid')
        seen.add(target)
        platform,arch=target
        name=('OfferSteady-Companion-Global-Setup-1.3.6-Windows-x64.exe' if platform=='windows'
              else f'OfferSteady-Companion-Global-1.3.6-macOS-{arch}.dmg')
        require(entry.get('version')=='1.3.6' and entry.get('protocolVersion')=='2.0'
                and entry.get('fileName')==name and entry.get('objectKey')==f'global-desktop-releases/{platform}/{arch}/1.3.6/{name}'
                and entry.get('distributionStatus')=='published' and entry.get('developmentOnly') is False
                and type(entry.get('fileSizeBytes')) is int and 0<entry['fileSizeBytes']<2_000_000_000
                and isinstance(entry.get('sha256'),str) and SHA.fullmatch(entry['sha256'])
                and entry.get('publishedAtMs')==payload['generatedAtMs'], 'global_manifest_metadata_invalid')
        require(not any(k in entry for k in ('localPath','artifactPath','zipPath')), 'private_metadata_in_manifest')
        require((entry.get('signingStatus')=='verified' and entry.get('notarized') is True and entry.get('minimumOs')=='macOS 14.2+')
                if platform=='macos' else
                (entry.get('signingStatus')=='unsigned' and entry.get('notarized') is False and entry.get('minimumOs')=='Windows 10 22H2+'), 'artifact_trust_metadata_invalid')
        matches=[p for p in proofs if (p.get('platform'),p.get('architecture'))==target]
        require(len(matches)==1 and matches[0].get('objectReadbackVerified') is True
                and matches[0].get('contentType')==('application/x-apple-diskimage' if platform=='macos' else 'application/vnd.microsoft.portable-executable')
                and all(matches[0].get(k)==entry.get(k) for k in ('version','fileName','fileSizeBytes','sha256','objectKey')), 'object_readback_does_not_match_manifest')
    require(seen==TARGETS, 'global_manifest_targets_missing')


def check_plan():
    plan=read_json(ROOT/'input.json')
    require(set(plan)=={'releaseId','baselines','candidates','allowedBackend','openapiBefore','openapiAfter',
        'supportFiles','publicRoutes','nonTargets','webInventory','runtimeBefore','ancillaryInputs'},'input_fields_changed')
    require(plan['releaseId']==RELEASE and set(plan['baselines'])==set(BASES)==set(plan['candidates'])=={'backend'},'component_scope_changed')
    b,c=plan['baselines']['backend'],plan['candidates']['backend']
    require((b.get('id'),b.get('image'))==BASES['backend'] and b.get('signature',{}).get('id')==b['id']
        and b['signature']['image']==b['image'] and b['startedAt']==b['signature']['startedAt'],'actual_baseline_changed')
    valid_inventory(b.get('inventory'));valid_inventory(c.get('inventory'));valid_inventory(c.get('rollbackInventory'))
    require(len(b['inventory'])==303 and digest(canonical(b['inventory']))==BASELINE_INVENTORY_SHA,'baseline_source_changed')
    require(set(plan['allowedBackend'])==set(APPROVED_BACKEND) and plan['allowedBackend']==APPROVED_BACKEND,'allowlist_changed')
    require(len(c['inventory'])==307 and set(c['inventory'])==set(b['inventory'])|ADDED_PATHS,'candidate_input_set_changed')
    changed={n:h for n,h in c['inventory'].items() if b['inventory'].get(n)!=h}
    require(changed==APPROVED_BACKEND,'candidate_delta_not_exact')
    require(c.get('image')==CANDIDATE_IMAGE and c.get('rollbackImage')==BASES['backend'][1]
        and c['rollbackInventory']==b['inventory'],'fixed_image_or_rollback_changed')
    require(b.get('settingsFields')==379 and isinstance(b.get('settingsSha256'),str) and SHA.fullmatch(b['settingsSha256']),'settings_contract_missing')
    require(plan['runtimeBefore']==RUNTIME_BEFORE and plan['ancillaryInputs']==ANCILLARY_INPUTS,'runtime_contract_changed')
    for key in ('openapiBefore','openapiAfter'):
        v=plan[key];schema=read_json(relative_file(v['path']))
        require(v['pathCount']==223 and v['schemaSha256']==SCHEMA_SHA and digest(canonical(schema))==SCHEMA_SHA,'schema_drift')
    require(plan['openapiBefore']==plan['openapiAfter'],'schema_delta_not_allowed')
    required={'controller.py','base_helpers.py','ownership_primitives.py','probe.py','entity_idle_gate.py',*GATES,TCP_GATE}
    require(set(plan['supportFiles'])==required,'support_scope_changed')
    for n,h in plan['supportFiles'].items():require(digest(relative_file(n).read_bytes())==h,'release_support_drift')
    require(plan['nonTargets']==NON_TARGETS and set(NON_TARGETS)==EXPECTED_NAMES-{'offersteady-global-backend-1'},'non_target_baseline_changed')
    require(plan['webInventory']==WEB_INVENTORY and len(WEB_INVENTORY)==251,'web_source_baseline_changed')
    require(plan['publicRoutes']==PUBLIC_ROUTES,'public_route_scope_changed')
    return plan


def expected_inventory(plan, service, kind):
    if kind=='baseline':
        return plan['baselines'][service]['inventory']
    return plan['candidates'][service]['inventory' if kind=='new' else 'rollbackInventory']


def progress_state():
    return read_json(ROOT/'progress.json') if (ROOT/'progress.json').exists() else {}


def baseline_stopped_proof(service,current):
    before=read_json(ROOT/service/'container-before.json')
    require((current['Id'],current['Image'])==BASES[service]
            and P.ownership_signature(current)==P.ownership_signature(before) and H.stopped_process(current), 'baseline_stopped_owner_unproven')
    again=inspect(current['Id'])
    require(H.stopped_process(again) and H.container_signature(again)==H.container_signature(current), 'baseline_stopped_owner_unstable')


def targets_owned(manifest,progress,*,recovery=False):
    restored=read_json(ROOT/'baseline-restores.json') if (ROOT/'baseline-restores.json').exists() else {}
    for service,target in manifest['targets'].items():
        current=inspect(target['container']);entry=progress.get(service)
        if entry:
            require((current['Id'],current['Image'])==(entry['id'],entry['image']), 'release_container_owner_changed')
            P.assert_context_owner(current,target,entry['kind'])
            same={k:v for k,v in H.container_signature(current).items() if k!='health'}=={k:v for k,v in entry['signature'].items() if k!='health'}
            if not same and recovery:
                P.recovery_process_proof(current,entry)
            else:
                require(same,'released_container_signature_changed')
        elif recovery and not current['State']['Running']:
            baseline_stopped_proof(service,current)
        else:
            before=read_json(ROOT/service/'container-before.json')
            require((current['Id'],current['Image'])==BASES[service] and P.ownership_signature(current)==P.ownership_signature(before), 'baseline_container_owner_changed')
            reference=restored[service]['signature'] if service in restored else H.container_signature(before)
            require({k:v for k,v in H.container_signature(current).items() if k!='health'}=={k:v for k,v in reference.items() if k!='health'}, 'baseline_signature_changed')


def check_non_targets(manifest):
    names=set(run(['docker','ps','-a','--format','{{.Names}}']).stdout.decode().splitlines())
    require(names==EXPECTED_NAMES, 'non_target_container_set_changed')
    require(set(manifest['nonTargets'])==EXPECTED_NAMES-{PROJECT+'-'+s+'-1' for s in BASES}, 'non_target_manifest_set_changed')
    for name,signature in manifest['nonTargets'].items():
        now=H.container_signature(inspect(name))
        if name==LEGACY_STOPPED_NAME:
            require(signature==LEGACY_STOPPED_SIGNATURE and now==LEGACY_STOPPED_SIGNATURE, 'historical_stopped_container_changed')
        require({k:v for k,v in now.items() if k!='health'}=={k:v for k,v in signature.items() if k!='health'}, 'non_target_container_changed')
    for name,tree in manifest['nonTargetNginx'].items():
        require(P.nginx_inputs(container=name)==tree, 'non_target_nginx_drift')


def check_files(manifest,plan):
    require(digest((ROOT/'input.json').read_bytes())==manifest['inputSha256'], 'input_manifest_drift')
    require(manifest.get('financialAnchorMs')==FINANCIAL_ANCHOR_MS, 'financial_anchor_changed')
    for relative,checksum in manifest['privateFiles'].items():
        require(digest(relative_file(relative).read_bytes())==checksum, 'private_snapshot_drift')
    for service,target in manifest['targets'].items():
        before=read_json(ROOT/service/'container-before.json');H.verify_frozen_files(target,before)
        for path,checksum in target['sourceHashes'].items():
            require(digest(Path(path).read_bytes())==checksum, 'production_compose_or_env_drift')
        require(digest(canonical(H.rendered(target)))==target['sourceRenderedSha'], 'production_render_drift')
        for kind in ('new','rollback'):
            overlay=Path(target[kind+'Overlay'])
            require(digest(overlay.read_bytes())==target[kind+'OverlaySha256'], 'release_overlay_drift')
            require(H.rendered(target,frozen=True,overlay=overlay)==H.expected_overlay(read_json(ROOT/service/'rendered-before.json'),service,target[kind+'Image']), 'unrelated_rendered_configuration_change')
    check_non_targets(manifest)


def stopped_web_inventory(current):
    response=run(['docker','cp',current['Id']+':/usr/share/nginx/html/.','-'],timeout=30)
    require(len(response.stdout)<=200*1024*1024, 'stopped_web_archive_too_large')
    result={}
    with tarfile.open(fileobj=io.BytesIO(response.stdout),mode='r:*') as archive:
        for member in archive:
            name=PurePosixPath(member.name)
            require(not name.is_absolute() and '..' not in name.parts, 'stopped_web_archive_unsafe')
            if member.isdir():
                continue
            require(member.isfile() and 0<=member.size<=100*1024*1024, 'stopped_web_archive_entry_invalid')
            key=str(name)
            if key.startswith('html/'):
                key=key[5:]
            require(key and key not in result, 'stopped_web_archive_duplicate')
            data=archive.extractfile(member).read();require(len(data)==member.size, 'stopped_web_archive_truncated')
            result[key]=digest(data)
    return result


def verify_sources(manifest,plan,progress,*,recovery=False):
    targets_owned(manifest,progress,recovery=recovery)
    for service,target in manifest['targets'].items():
        current=inspect(target['container']);kind=progress.get(service,{}).get('kind','baseline')
        if current['State']['Running']:
            actual=P.inventory(service)
        else:
            require(recovery, 'unexpected_stopped_target')
            if service not in progress:
                baseline_stopped_proof(service,current)
            else:
                require(H.stopped_process(current) and P.ownership_signature(current)==progress[service]['ownershipSignature'], 'stopped_source_owner_unproven')
            actual=stopped_web_inventory(current) if service=='web' else P.stopped_source_inventory(current)
            again=inspect(current['Id']);require(H.stopped_process(again) and H.container_signature(again)==H.container_signature(current), 'stopped_source_owner_unstable')
        require(actual==expected_inventory(plan,service,kind), 'runtime_source_drift')


def verify_runtime(manifest,plan,progress,*,final=False):
    targets_owned(manifest,progress);check_files(manifest,plan);verify_sources(manifest,plan,progress)
    for service,target in manifest['targets'].items():
        current=inspect(target['container']);kind=progress.get(service,{}).get('kind','baseline')
        require(current['State']['Running'] and current['RestartCount']==0, 'target_not_running')
        if service=='backend':
            require(current['State'].get('Health',{}).get('Status')=='healthy', 'backend_unhealthy')
            require(P.settings(service)==read_json(ROOT/service/'settings-before.private.json'), 'effective_settings_drift')
        else:
            require(P.nginx_inputs(container=current['Id'])==read_json(ROOT/'web/nginx-before.json'), 'runtime_nginx_drift')
        if service in progress:
            P.runtime_invariant(read_json(ROOT/service/'container-before.json'),current,target,kind)
        if final:
            require(kind=='new', 'partial_release_not_complete')
    verify_unchanged_contracts()
    expected=plan['openapiAfter'] if progress.get('backend',{}).get('kind')=='new' else plan['openapiBefore']
    actual=P.schema();require(digest(canonical(actual))==expected['schemaSha256'] and len(actual['paths'])==expected['pathCount'], 'runtime_api_schema_drift')


def candidate_probe(target,plan,*,rollback=False):
    image=target['rollbackImage'] if rollback else target['newImage']
    if rollback:
        require(P.inventory('backend',image=image)==plan['baselines']['backend']['inventory'],'rollback_source_changed')
        H.verify_image_base(inspect(image),inspect(BASES['backend'][1]))
        save('backend/offline-probe-rollback.json',{'passed':True,'exactOriginalImage':True,'sourceInputs':303})
        return
    command=['docker','run','--rm','-i','--network','none','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--pids-limit','64','--memory','768m',
        '--env-file',str(ROOT/'backend/runtime.env.private'),'-e','OFFERSTEADY_RELEASE_PROBE_IMAGE='+image,
        '--workdir','/app/apps/backend','--entrypoint','python',image,'-B','-']
    value=json.loads(run(command,input=(SUPPORT/'probe.py').read_bytes(),timeout=90).stdout)
    require(value.get('passed') is True and value.get('image')==image and value.get('runtimeFiles')==307
        and value.get('httpPaths')==223 and value.get('settingsCount')==379 and value.get('dependencyCount')==46
        and value.get('allSyntheticWorkersReleased') is True and value.get('lifespanEntered') is False
        and value.get('pinnedPairingTransportCalls')==[3,3,3]
        and all(type(value.get(k)) is int and value[k]==0 for k in ('databaseOperations','networkRequests','fileWrites')),'offline_probe_failed')
    save('backend/offline-probe-new.json',value)


def prepare():
    plan=check_plan();require(not (ROOT/'prepared.json').exists(),'already_prepared')
    require(set(run(['docker','ps','-a','--format','{{.Names}}']).stdout.decode().splitlines())==EXPECTED_NAMES,'component_set_changed')
    before=inspect(PROJECT+'-backend-1');b=plan['baselines']['backend'];c=plan['candidates']['backend']
    require(H.container_signature(before)==b['signature'] and before['State']['Running'] and before['RestartCount']==0
        and before['State'].get('Health',{}).get('Status')=='healthy','fresh_runtime_baseline_changed')
    require(P.inventory('backend')==b['inventory']==P.inventory('backend',image=b['image']),'runtime_source_changed')
    require(digest(canonical(P.schema()))==SCHEMA_SHA,'fresh_schema_drift')
    verify_single_writer()
    manifest={'inputSha256':digest((ROOT/'input.json').read_bytes()),'financialAnchorMs':FINANCIAL_ANCHOR_MS,
        'targets':{},'nonTargets':{},'nonTargetNginx':{},'privateFiles':{},'proxyStaticBackendUpstreams':{}}
    target=H.freeze(before,'backend');target.update(newImage=c['image'],rollbackImage=c['rollbackImage'])
    settings=P.settings('backend')
    require(len(settings)==379 and P.settings_sha(settings)==b['settingsSha256'],'settings_drift')
    save('backend/settings-before.private.json',settings);P.write_env(ROOT/'backend/runtime.env.private',environment(before))
    for kind,key in (('new','image'),('rollback','rollbackImage')):
        H.verify_image_base(inspect(c[key]),inspect(b['image']))
        require(P.inventory('backend',image=c[key])==expected_inventory(plan,'backend',kind),'candidate_inventory_drift')
        overlay=ROOT/'backend'/(kind+'.compose.json');write_json(overlay,{'services':{'backend':{'image':c[key]}}})
        target[kind+'Overlay']=str(overlay);target[kind+'OverlaySha256']=digest(overlay.read_bytes())
        require(H.rendered(target,frozen=True,overlay=overlay)==H.expected_overlay(read_json(ROOT/'backend/rendered-before.json'),'backend',c[key]),'unrelated_configuration_change')
    manifest['targets']['backend']=target
    for n in NON_TARGETS:
        value=H.container_signature(inspect(n));require(value==NON_TARGETS[n],'fresh_non_target_changed');manifest['nonTargets'][n]=value
    for n in (PROJECT+'-web-1',PROJECT+'-admin-1'):
        manifest['nonTargetNginx'][n]=P.nginx_inputs(container=n)
        require(manifest['nonTargetNginx'][n]==NGINX_INPUTS[n],'proxy_inputs_changed')
        raw=run(['docker','exec',n,'nginx','-T']).stdout
        manifest['proxyStaticBackendUpstreams'][n]=bool(re.search(rb'(?m)^\s*(?:proxy_pass\s+https?://|server\s+)(?:backend|offersteady-global-backend-1)(?::8000)?(?:[;/\s])',raw))
    candidate_probe(target,plan);candidate_probe(target,plan,rollback=True)
    for p in (ROOT/'backend').rglob('*'):
        if p.is_file() and p.name not in {'new.compose.json','rollback.compose.json'}:manifest['privateFiles'][str(p.relative_to(ROOT))]=digest(p.read_bytes())
    save('prepared.json',manifest);verify_runtime(manifest,plan,{})
    idle_gates(manifest);tcp_gate(manifest,{})
    emit(prepared=True,productionChanged=False,components=1)


def gate_command(manifest):
    require(manifest.get('financialAnchorMs')==FINANCIAL_ANCHOR_MS, 'financial_anchor_changed')
    before=read_json(ROOT/'backend/container-before.json');network=before['HostConfig']['NetworkMode']
    require(isinstance(network,str) and re.fullmatch('[A-Za-z0-9_.-]+',network) and network not in {'host','none'}, 'gate_network_invalid')
    return ['docker','run','--rm','-i','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--pids-limit','64','--memory','512m','--network',network,'--env-file',str(ROOT/'backend/runtime.env.private'),
            '-e','OFFERSTEADY_RELEASE_ORIGINAL_BACKEND_STARTED_AT_MS='+str(FINANCIAL_ANCHOR_MS),
            '--workdir','/app/apps/backend','--entrypoint','python',BASES['backend'][1],'-B','-']


def idle_gates(manifest):
    verify_single_writer()
    records=P.idle_gates(manifest)
    entity_idle_gate(manifest)
    return records


def tcp_gate(manifest,progress,*,recovery=False):
    current=inspect(PROJECT+'-backend-1')
    if recovery and 'backend' not in progress and not current['State']['Running']:
        baseline_stopped_proof('backend',current)
        save('last-tcp-idle-gate.json',{'passed':True,'method':'twice_proven_stopped_baseline'})
        return
    return P.tcp_gate(manifest,progress,recovery=recovery)


def reconcile_intent(manifest,progress):
    path=ROOT/'switch-intent.json'
    if not path.exists():return
    intent=read_json(path)
    if progress!=intent['previousProgress']:return
    service,kind=intent['service'],intent['kind'];require(service in BASES and kind in {'new','rollback'}, 'switch_intent_invalid')
    target=manifest['targets'][service];now=inspect(target['container'])
    if now['Image']==target[kind+'Image'] and now['Config']['Labels'].get('com.docker.compose.project.config_files')==','.join(target['frozenComposeFiles']+[target[kind+'Overlay']]):
        P.record_created_owner(target,kind,intent['beforeId'],now,progress)


def refresh_static_proxies(manifest,plan,progress):
    check_plan();check_files(manifest,plan);verify_sources(manifest,plan,progress)
    idle_gates(manifest);tcp_gate(manifest,progress)
    refreshed=[]
    for name,needed in manifest['proxyStaticBackendUpstreams'].items():
        require(name in {PROJECT+'-web-1',PROJECT+'-admin-1'} and type(needed) is bool, 'proxy_refresh_scope_changed')
        if needed:
            check_non_targets(manifest);targets_owned(manifest,progress)
            run(['docker','exec',name,'nginx','-t']);run(['docker','exec',name,'nginx','-s','reload'])
            check_non_targets(manifest);targets_owned(manifest,progress);refreshed.append(name)
    save('proxy-refresh.json',{'proxyReloaded':refreshed,'onlyAfterBackendIpChange':True,'configurationChanged':False})


def switch(manifest,plan,progress,service,kind):
    require(service in BASES and kind in {'new','rollback'}, 'switch_scope_invalid')
    check_plan();check_files(manifest,plan);verify_sources(manifest,plan,progress,recovery=kind=='rollback')
    idle_gates(manifest);tcp_gate(manifest,progress,recovery=kind=='rollback')
    check_plan();check_files(manifest,plan);targets_owned(manifest,progress,recovery=kind=='rollback')
    target=manifest['targets'][service];before=inspect(target['container'])
    save('switch-intent.json',{'service':service,'kind':kind,'beforeId':before['Id'],'previousProgress':deepcopy(progress)})
    try:
        run(H.compose_args(target,frozen=True,overlay=target[kind+'Overlay'])+['up','-d','--no-build','--no-deps','--pull','never',service],timeout=120)
    finally:
        now=inspect(target['container'])
        if now['Image']==target[kind+'Image'] and now['Config']['Labels'].get('com.docker.compose.project.config_files')==','.join(target['frozenComposeFiles']+[target[kind+'Overlay']]):
            P.record_created_owner(target,kind,before['Id'],now,progress)
            P.runtime_invariant(read_json(ROOT/service/'container-before.json'),now,target,kind)
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        now=inspect(target['container'])
        if now['State']['Running'] and now['RestartCount']==0 and (service!='backend' or now['State'].get('Health',{}).get('Status')=='healthy'):break
        time.sleep(1)
    else:raise GuardError('target_health_failed')
    P.runtime_invariant(read_json(ROOT/service/'container-before.json'),now,target,kind)
    require(P.inventory(service)==expected_inventory(plan,service,kind), 'released_source_drift')
    if service=='backend':
        ips=lambda item:{n:v.get('IPAddress') for n,v in item['NetworkSettings']['Networks'].items()}
        if ips(before)!=ips(now):refresh_static_proxies(manifest,plan,progress)


def public_checks(plan,progress):
    for path,name in PUBLIC_ROUTES.items():
        with urlopen(Request('https://offersteady.com'+path,headers={'Cache-Control':'no-cache','Accept-Encoding':'identity'}),timeout=15) as response:
            require(response.status==200 and digest(response.read())==WEB_INVENTORY[name],'public_route_bytes_changed')
    with urlopen('https://offersteady.com/healthz',timeout=15) as response:
        require(response.status==200 and json.load(response)['data']['status']=='ok','public_health_failed')


def verify():
    plan=check_plan();manifest=read_json(ROOT/'prepared.json');progress=progress_state();reconcile_intent(manifest,progress)
    verify_runtime(manifest,plan,progress,final=True);public_checks(plan,progress)
    save('verified.json',{'atMs':int(time.time()*1000),'verified':True,'services':list(BASES),'nonTargetsUnchanged':True})
    emit(verified=True,components=1,nonTargetsUnchanged=True,financialAnchorMs=FINANCIAL_ANCHOR_MS)


def restore_stopped_baseline(manifest,plan,progress,service):
    current=inspect(manifest['targets'][service]['container']);baseline_stopped_proof(service,current)
    check_files(manifest,plan);verify_sources(manifest,plan,progress,recovery=True);idle_gates(manifest);tcp_gate(manifest,progress,recovery=True)
    baseline_stopped_proof(service,inspect(current['Id']))
    try:run(['docker','start',current['Id']],timeout=60)
    finally:
        now=inspect(current['Id'])
        if now['State']['Running']:
            require(P.ownership_signature(now)==P.ownership_signature(current), 'restored_baseline_owner_changed')
            restores=read_json(ROOT/'baseline-restores.json') if (ROOT/'baseline-restores.json').exists() else {}
            restores[service]={'id':now['Id'],'image':now['Image'],'signature':H.container_signature(now)};save('baseline-restores.json',restores)


def rollback():
    plan=check_plan();manifest=read_json(ROOT/'prepared.json');progress=progress_state();reconcile_intent(manifest,progress)
    check_files(manifest,plan);verify_sources(manifest,plan,progress,recovery=True)
    for service in BASES:
        if service not in progress and not inspect(manifest['targets'][service]['container'])['State']['Running']:
            restore_stopped_baseline(manifest,plan,progress,service)
    for service in BASES:
        if progress.get(service,{}).get('kind')=='new':switch(manifest,plan,progress,service,'rollback')
    verify_runtime(manifest,plan,progress);require(all(p['kind']=='rollback' for p in progress.values()), 'rollback_incomplete')
    public_checks(plan,progress);save('rolled-back.json',{'restored':True,'atMs':int(time.time()*1000)})
    emit(rollbackSucceeded=True,compatibilityDownloadsPreserved=True)


def deploy(*,preflight=False):
    plan=check_plan();manifest=read_json(ROOT/'prepared.json');progress=progress_state();reconcile_intent(manifest,progress)
    require(not (ROOT/'rolled-back.json').exists(), 'release_already_rolled_back')
    if (ROOT/'deployed.json').exists():
        verify();return emit(alreadyDeployed=True,productionChanged=False)
    if all(progress.get(s,{}).get('kind')=='new' for s in BASES):
        verify_runtime(manifest,plan,progress,final=True);public_checks(plan,progress)
        if not preflight:save('deployed.json',{'deployed':True,'atMs':int(time.time()*1000),'reconciledCompletedSwitch':True})
        return emit(alreadyDeployed=True,productionChanged=False)
    verify_runtime(manifest,plan,progress);idle_gates(manifest);tcp_gate(manifest,progress)
    if preflight:return emit(preflightPassed=True,productionChanged=False)
    try:
        for service in BASES:
            if progress.get(service,{}).get('kind')!='new':
                verify_runtime(manifest,plan,progress);switch(manifest,plan,progress,service,'new')
        verify_runtime(manifest,plan,progress,final=True);public_checks(plan,progress)
        save('deployed.json',{'deployed':True,'atMs':int(time.time()*1000),'services':list(BASES)})
        emit(deployed=True,components=1,nonTargetsUnchanged=True,financialAnchorMs=FINANCIAL_ANCHOR_MS)
    except Exception as exc:
        # Drift and unavailable/busy gates never authorize automatic overwrite.
        if isinstance(exc,GuardError) and str(exc)!='target_health_failed':raise
        restored=False
        try:rollback();restored=True
        except Exception:pass
        save('failed-cutover.json',{'failed':True,'rollbackSucceeded':restored})
        raise GuardError('cutover_failed_rollback_'+('succeeded' if restored else 'needs_attention')) from None


@contextmanager
def release_lock():
    with (ROOT/'release.lock').open('a') as stream:
        try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise GuardError('another_release_action_is_running') from None
        try:yield
        finally:fcntl.flock(stream,fcntl.LOCK_UN)


def main():
    os.umask(0o077);bind_primitives()
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',nargs='?',default='preflight',choices=('prepare','preflight','deploy','verify','rollback'))
    action=parser.parse_args().action
    try:
        require(ROOT.is_dir() and not ROOT.is_symlink() and ROOT.resolve()==ROOT, 'private_release_directory_missing')
        with release_lock():
            {'prepare':prepare,'preflight':lambda:deploy(preflight=True),'deploy':deploy,'verify':verify,'rollback':rollback}[action]()
    except Exception as exc:
        reason=str(exc) if isinstance(exc,GuardError) and re.fullmatch('[a-z0-9_]+',str(exc)) else 'release_operation_failed_private_diagnostics_only'
        emit(ok=False,reason=reason);raise SystemExit(75 if reason=='protected_user_work_cutover_deferred' else 1) from None


def verify_unchanged_contracts():
    require(P.inventory('web')==WEB_INVENTORY,'non_target_web_source_changed')
    current=inspect(PROJECT+'-backend-1')
    metadata=json.loads(run(['docker','exec',current['Id'],'python','-B','-c',"import importlib.metadata,json,platform;print(json.dumps({'python':platform.python_version(),'dependencies':dict(sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions()))}))"]).stdout)
    require(metadata==RUNTIME_BEFORE,'runtime_dependencies_changed')
    for n,h in ANCILLARY_INPUTS.items():require(digest(H.read_container(current['Id'],'/app/'+n))==h,'auxiliary_input_changed')
    verify_single_writer()


def verify_single_writer():
    current = inspect('offersteady-global-backend-1')
    names = run(['docker', 'ps', '--filter', 'label=com.docker.compose.service=backend', '--format', '{{.Names}}']).stdout.decode().splitlines()
    require(names == (['offersteady-global-backend-1'] if current['State']['Running'] else []), 'single_backend_container_unproven')
    entrypoint, arguments = current['Config'].get('Entrypoint') or [], current['Config'].get('Cmd') or []
    require(type(entrypoint) is list and type(arguments) is list,
            'single_writer_command_unproven')
    command = entrypoint + arguments
    require(command and all(type(value) is str and value for value in command), 'single_writer_command_unproven')
    executable = Path(command[0]).name
    if executable == 'uvicorn':
        server_command = command
    elif re.fullmatch(r'python(?:[0-9]+(?:\.[0-9]+)*)?', executable) and command[1:3] == ['-m', 'uvicorn']:
        # The actual fixed Backend image starts the module with python -m;
        # accept this exact form without admitting shells or wrapper scripts.
        server_command = command[2:]
    else:
        raise GuardError('single_writer_command_unproven')
    require(len(server_command) >= 2 and server_command[1] == 'app.main:app'
            and '--reload' not in server_command, 'single_writer_command_unproven')
    env = environment(current)
    workers = env.get('WEB_CONCURRENCY', '1')
    for i, value in enumerate(server_command):
        if value == '--workers':
            require(i + 1 < len(server_command), 'single_writer_command_unproven')
            workers = server_command[i + 1]
        elif value.startswith('--workers='):
            workers = value.split('=', 1)[1]
    require(str(workers) == '1' and not env.get('GUNICORN_CMD_ARGS'), 'single_writer_config_unproven')
    if not current['State']['Running']:
        require(H.stopped_process(current), 'single_writer_stopped_process_unproven')
        return
    code = """from pathlib import Path
import json
rows=[]
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:
        rows.append(path.read_bytes().split(bytes([0])))
    except (FileNotFoundError, ProcessLookupError):
        continue

def server(args):
    if not args:
        return False
    name=args[0].split(b'/')[-1]
    if name in (b'uvicorn',b'gunicorn'):
        return True
    if not name.startswith(b'python'):
        return False
    return (b'--multiprocessing-fork' in args or len(args)>1 and args[1].split(b'/')[-1] in (b'uvicorn',b'gunicorn')
            or len(args)>2 and args[1]==b'-m' and args[2] in (b'uvicorn',b'gunicorn',b'multiprocessing.spawn'))
print(json.dumps({'serverProcesses':sum(server(args) for args in rows)}))
"""
    try:
        value = json.loads(run(['docker', 'exec', current['Id'], 'python', '-B', '-c', code]).stdout)
    except Exception:
        raise GuardError('single_writer_process_read_failed') from None
    require(isinstance(value, dict) and set(value) == {'serverProcesses'}
            and type(value['serverProcesses']) is int and value['serverProcesses'] == 1, 'single_writer_process_count_unproven')
    after = inspect(current['Id'])
    require(H.container_signature(after) == H.container_signature(current), 'single_writer_owner_changed')


def entity_idle_gate(manifest):
    # This standalone read-only gate understands the new namespace even when
    # executed with the baseline image. It must never instantiate a writer repo.
    try:
        response = subprocess.run(gate_command(manifest), input=(SUPPORT / 'entity_idle_gate.py').read_bytes(), capture_output=True, timeout=25)
        value = json.loads(response.stdout)
    except Exception:
        raise GuardError('protected_entity_gate_unavailable') from None
    # Exact numeric contract is supplied by the independently reviewed gate.
    validate_entity_gate(value, response.returncode)


def validate_entity_gate(value, returncode):
    protected = {'activeCnBindings', 'activeCnCandidates', 'pendingCnCandidateClaims', 'recentCnEntityWrites',
                 'unknownCnSessionStates', 'invalidCnEntityMetadata', 'cnEntityReadFailures',
                 'cnEntityScanLimitExceeded', 'cnEntityMutationDetected'}
    informational = {'cnBoundBindings', 'cnStaleBindings', 'cnRetiredBindings', 'cnCandidates',
                     'cnRetiredCandidates', 'cnHistoricalEntities', 'scannedCnEntityRecords'}
    require(isinstance(value, dict) and set(value) == protected | informational | {'atMs'}
            and all(type(v) is int and v >= 0 for v in value.values())
            and 0 <= int(time.time() * 1000) - value['atMs'] <= 10000
            and returncode in {0, 75}, 'protected_entity_gate_unavailable')
    save('last-entity-idle-gate.json', value)
    unknown = {'unknownCnSessionStates', 'invalidCnEntityMetadata', 'cnEntityReadFailures', 'cnEntityScanLimitExceeded'}
    require(not any(value[k] for k in unknown), 'protected_entity_gate_unavailable')
    busy = any(value[k] for k in protected)
    require((returncode == 75) == bool(busy), 'protected_entity_gate_unavailable')
    require(not busy, 'protected_user_work_cutover_deferred')


bind_primitives()
if __name__=='__main__':main()
