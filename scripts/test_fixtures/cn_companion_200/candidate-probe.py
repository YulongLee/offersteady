"""Offline actual-image CN shared-blocking probe; one expectation map.

Run with --network=none --read-only --cap-drop=ALL and server-local settings.
Never enter application lifespan or call a database/provider. Every fixture is
synthetic. Only named synthetic/control/CN-I/O workers may start; all are joined
before success. No production value or synthetic identifier is output.

EXPECTED keys: inventory, python, dependencies, settingsSha256, openapiSha256,
httpPaths and ancillary. The controller must obtain ancillary from the actual
baseline image, then supply its fixed material-upload-formats.json path/SHA.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import importlib.metadata
import json
import logging
from math import isfinite
import os
from pathlib import Path
import platform
import re
import socket
import sys
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

EXPECTED = {'inventory': {'ai/prompts/README.md': 'acf349b25a322e5fca2e48127366f31e0289c65e7b0fb62849a0aef24a0de614', 'ai/prompts/chat-service/continuation.en.md': '95989b17e55324a7b82e042608315abf1f8477600424d1e2f3b90f15b257f426', 'ai/prompts/chat-service/continuation.md': 'd4b4880b802f4573da9c9d1c7837ab1d0f87a44c2a96541ed3c95d130c4df64a', 'ai/prompts/chat-service/detail.en.md': 'b4984f9be58d6d4b4f0819e21fffab66795bcd6b2afd2240d5384349fc10f255', 'ai/prompts/chat-service/detail.md': '7c7efcda04559435ab91044b0439d037e82201deb5a9f114c01fc757f11b21d0', 'ai/prompts/chat-service/quick.en.md': '26443efd71ada5c230ffe25211a08994d26af084d223d29a388a06f85306e738', 'ai/prompts/chat-service/quick.md': '8b20f1783abafbb1980f3c3d5cee7e165d359d5249df864bcaa2fe1f2a514372', 'ai/prompts/chat-service/system-v3.md': '1e640d13e62d39aae5423c86c0b616af42ae4a36f1cecec8104c3b70c8e9dcef', 'ai/prompts/chat-service/system.en.md': '81f09c9e6f6fe01efc80dbb4b8cd182508d889854ac27a3281c11e72538bc269', 'ai/prompts/chat-service/system.md': 'e84d13f4e140edfe8b45b776c9ba05e8273b58b54bb14afa8b7d80d3f9eb8b1d', 'ai/prompts/mock-interview/README.md': 'c0a4d9600a0c3a480ba633761b418873911eb19a6242d6a446697ee0fc22aa58', 'ai/prompts/mock-interview/answer-structure.md': '4ef41e892499bffe67558b837e6b4a5c70f10533c9b247f840cd036c99b83d96', 'ai/prompts/mock-interview/question.md': '8fd1fbc0ef6f6e7abc641f548d2e2fee35db04d80c57a1dde787ff7c225c63cd', 'ai/prompts/mock-interview/report.md': '2a3d09711b7eb3dbcdbf0187d71f6dccbe210cbc7addfb147a5a8645f4ac249d', 'ai/prompts/mock-interview/tts.txt': 'a40515717c54dba2ce20b3f8c1d4f2955252fa7b5f3934e0ba08e1ba207bc67c', 'ai/prompts/programming-policy/policy.en.md': '219670eed2f0c2cbcdc3c50cdac29ff1d68f1fe63da05e92f9a9a634ccbca011', 'ai/prompts/programming-policy/policy.md': '47368570999be8ed50070f6e280c5e5bdb205a836fd140f71a76119f4cfdeb74', 'ai/prompts/resume-optimizer/review.zh-CN.v1.md': '38c5be209ebb1273ac3e9e5e6bcf403add52517b1009869159ec01c36e50f2fb', 'ai/prompts/resume-optimizer/review.zh-CN.v2.md': '58cfa54bca5556aaa7640b3bd9da5761369c4afbddd2c96ef67c0c26dee6cd80', 'ai/prompts/screenshot-answer/system-v1.md': 'a5439942e8a421cfe9e6e8c4fdce71678bb8be22991582a82e2e2e7d2a349e0b', 'ai/prompts/screenshot-answer/system.en.md': 'b868664c2f8feba31763c2749d28ccf96277e05a1bebac7c4f732e21c746584b', 'ai/prompts/screenshot-answer/system.md': 'edd6812d53240ba6ab249c4803679ee960f2b1382a514735cd6120df382c1068', 'apps/backend/app/__init__.py': 'c7a401fa1dbc4189255d002741ff7ab4a30bf0c64b25d2bcdc987b88723bed5a', 'apps/backend/app/adapters/__init__.py': '5384bfdb2df380b6557cc7a71d16891415bccaa87699406e236f752c6415389f', 'apps/backend/app/adapters/oss_storage.py': 'ac84828377f8a9c1b0ec83d1d303497a45d34f66067760d2956dba159794ad5d', 'apps/backend/app/api/__init__.py': '5645d3ba205ea9d1a0e80fd4b2381fde91e928b9e2263ddb32578704addac9d7', 'apps/backend/app/api/admin.py': '4470bb1bc472943e8ed4a9a42cb2b3fb7a6292499af4c542d345d3df2fd95824', 'apps/backend/app/api/admin_promotion.py': 'c275dcc34545a6a08d872d94d9fbec9f36002aaf1fd0c61482252fd8bbe3d056', 'apps/backend/app/api/promotion.py': 'c3ae744fd8233b866c6fb490771c80b6b6691a19965d7c940a84e3b24e48a764', 'apps/backend/app/api/routers/__init__.py': '6a4d3814ef27df4a3fa435f48fe7e244c40c3ecd1de8b260c010988cb6e5f3fb', 'apps/backend/app/api/routers/system.py': 'b893fe4e816bad3c4af43e1a8e4bbb1f285e8ae543d9c86675a1309e04b4eee1', 'apps/backend/app/api/v1.py': '3a84002f1e839da1c788473fe6a72c6e548fe16646e64a8800b4b703a914f7e1', 'apps/backend/app/assets/resume-optimizer/NotoSansCJKsc-Regular.ttf': 'fa2124fd2197ba2f050d48e1e66284d0aa00900657897eec679ab04d2913c429', 'apps/backend/app/assets/resume-optimizer/OFL.txt': '6a73f9541c2de74158c0e7cf6b0a58ef774f5a780bf191f2d7ec9cc53efe2bf2', 'apps/backend/app/assets/resume-optimizer/source.json': 'ded280036992b432cbc44134c0c1f8a910565ae5bbd4ae41e8b5859af1031174', 'apps/backend/app/core/config.py': '235c4fb54c93e704fa314ebd0b3f877e3f00b48635b30c0baa4a7c4a93178735', 'apps/backend/app/core/errors.py': 'f821ad52cfa04117dd8d9888dded51f3293f6e3a68b1dc4bb11a51672fd3bee3', 'apps/backend/app/core/logging.py': '1cfd23c7bf714cd2dd9c45ea6d439c906633d755bf575f616d526c3f90cbb9ad', 'apps/backend/app/core/request_context.py': '2b1d072915927ef1b4a5eb7efef93840a00c079fcb88a6242061331042e60fce', 'apps/backend/app/core/responses.py': '4cedbe41efae8655846467d8136a23cb57aa8a834917fb716c433bad5f5b8c18', 'apps/backend/app/deps.py': 'a8f290b49636275de85e9cd3de69133d91155b30653ddf5ae39efc0220b6da5a', 'apps/backend/app/desktop_release_manifest.json': '6cb2a0e01afa7c8539a1cccdb1f0d0c8dd1907304ffe71711438ae6b70061340', 'apps/backend/app/interview_languages.py': 'f014c7e55fd6758ff1c44dc0a1d605b6e2b012fc0c98e4051147d96e5a966de6', 'apps/backend/app/main.py': '309809b0919ffa1289922d17b17a850e75f96104d1508ef9e0253cc2b9cb7286', 'apps/backend/app/material_formats.py': 'efab7d20e8288f570ab8652d1130f3b7ed2edb8fd11630af9f97a69fd8bb0172', 'apps/backend/app/middleware/request_context.py': '61eb30de386a04d1e948b439a30295aff4e84192fda97773bc838ac6347b0da3', 'apps/backend/app/modules/__init__.py': 'b45973b814e6ae9d0a608f5ae7422cf0143f1e956d61e30d08201177c7da2a78', 'apps/backend/app/modules/authentication.py': '77e74aa24dd10a5f4ea39e4ba6a5a93831382cbbb81f9acc4245ef97eb04cdc2', 'apps/backend/app/modules/billing.py': '9528378a10e381e43b284ecaa19d94e7d0e09c0496753c60520aa71a4ed87b9f', 'apps/backend/app/modules/cn_resume_optimizer.py': '8ac13e3ee38cd79324601ea3d82421522bdea52ddb029fd8914fa27bf0c3868b', 'apps/backend/app/modules/common.py': '0469c3a903f5a0ce35cc16452a1e40262330ec5915e2ab09e0e2346421ad1e2d', 'apps/backend/app/modules/document_processing.py': 'fe24f901343c16b1184077cf522fc9fc214bc579e3b27cf16365fe9dbee3d503', 'apps/backend/app/modules/document_service.py': 'a92094ba4e484e6ca0f5a6ac9b29375efcfd971ba191d4c09c5d7d5959985574', 'apps/backend/app/modules/job_description.py': '37a3083bafa1cfdb59edce391b5ff810cc4515763cf9bfa504d8210d18bc84e2', 'apps/backend/app/modules/knowledge.py': 'd2bb9662defbd6d685bff6e44f0a56d29551cfc829e217b2812b555e2e8239df', 'apps/backend/app/modules/knowledge_retrieval.py': '9dadab5f7884fdef3642f371b3e40a7a646f19f4fd5b3d43307fa8fde05d657e', 'apps/backend/app/modules/live_answer.py': '542706aecf1ac4801767280d6776dfe542a111d29d5d606db5b37510580b148f', 'apps/backend/app/modules/mock_interview.py': '8440326d43aa1a14fef76d907d2b608496aaa533b354e4934fe6abeb1e96e40c', 'apps/backend/app/modules/mock_interview_legacy.py': '7b36d6c9f14a3d625a7ac645e3ca79ea9f0751c1bd43e4deaf6ddf1d387e9b9e', 'apps/backend/app/modules/partner_program.py': '2f6a3e5875e39b3362548a5c63c6748efb8a8946c44a842e292e6e33ef1515f6', 'apps/backend/app/modules/realtime_speech.py': '8cf94a4a06828905baf88197983ba58ccf737e8648a11b42d32d391a0663fb1f', 'apps/backend/app/modules/resume.py': '08b8bcb11fa2c52f7a2506410b1b8f331c456c4ad9eb4776155786dfc3f22a45', 'apps/backend/app/modules/screenshot_answer.py': 'ec37a2b84cb609ee3e943b645fad36018d0d5cef8fc9113e098bbf4ef36b2e85', 'apps/backend/app/modules/session.py': '12b4b1cef0cd108a194ee16a1bec6627c546dd77439ee19042019f54c756d74a', 'apps/backend/app/modules/system.py': '8826eecc3e26b7436f4a0c262f47bd8b35e6d774f8078c7a99a8e494aa8eb188', 'apps/backend/app/modules/web.py': 'e4865462d344f579db425414fecf06a74378ac6e70df22c74337c3813d26d3a0', 'apps/backend/app/platform/cn_device_status_timing.py': '502d1578b076f326a3409d32804bdff20e3ceca4f4cfff5133dfa668efee0a99', 'apps/backend/app/platform/cn_hot_database.py': 'a53556b0d30cd452132f7cfdbab6c70d6cd73c14aa3e5b77639213e619560885', 'apps/backend/app/platform/cn_realtime_lifespan.py': '572bf67ae1043604465d19df0574b7b5bcb04daaaeadc46f334598a61d8defc9', 'apps/backend/app/platform/cn_realtime_loop_monitor.py': 'b464a83bcc35744d80ef76cf6a2c2760df0590b207c85039c9ff6885ab5c61d5', 'apps/backend/app/platform/database.py': '99deb33b4b3f5c85973187dae12b2d02a99e2b53ec1c7d1e959f31c7271b1ce2', 'apps/backend/app/platform/object_storage.py': 'e8ff28890f56ccebcb79445f506d5695d802b08fd3e32d54284de7d745afe12a', 'apps/backend/app/platform/pgvector.py': '848cbf97964325afa85bde6971d424f64a92a3245b5af35270486498f445203d', 'apps/backend/app/platform/retrieval_boundary.py': '79ddddb72f04b7e5ef459aa78f26ae3c2316b27f4cbccc1ee728fd42bfe94a01', 'apps/backend/app/ports/answer_generation.py': '00c5ff8e5466a200c283f1c4dc67379f3f59e08461a18dcb160821c4838f1077', 'apps/backend/app/ports/authentication.py': '864612b3b24d546b63e12532afd03c22735b05c09c05ea3938edcad31cdd3d27', 'apps/backend/app/ports/billing_persistence.py': '7eb776322891efee2b45ddff5846729cf504c45a7ec5be91b729f0881fb4a062', 'apps/backend/app/ports/chat.py': 'a9c55c281724e937e7b3d8b109f531b2026b08edef1a312c9a2a7d5b19ec8e98', 'apps/backend/app/ports/commercial_hardening.py': '8d2bba33c5e65a278d198f1ea7811da1fa3928b56762da3395202a7ff3f05955', 'apps/backend/app/ports/document_processing.py': '3c602c00d60c06fc59810d583ae2f1775fbf4c709f00722a0136b89b9c3e7495', 'apps/backend/app/ports/document_repository.py': '10d629aad531a82c7e6040a9d9a39e4d71501b261adfa9b9b16a474f40c8ae7c', 'apps/backend/app/ports/interview_session.py': '12c24f45489530ffc04e38ab1558f80466651a430e9c05f495ebdd768f79977c', 'apps/backend/app/ports/parsing.py': '6c31b5c36888525a24290a7079f6cc48b5b6a3d7079d7bd07b69180aa081e50c', 'apps/backend/app/ports/points_redemption.py': '60bd1278fcfd24575452dd6a8cb336852766b7ee01380b00ef0c4414cab3f0df', 'apps/backend/app/ports/realtime_speech.py': '83df0aa69d2ab4c09978d07591e8ddfe77a67c4b98674321189e6511cd07d98b', 'apps/backend/app/ports/retrieval.py': '118adb630c0c81dbaf1217d13047332e7747c2f33b645a0dd4c4b383fa0c3540', 'apps/backend/app/ports/screenshot_analysis.py': '205ead9dd8acf932e790f675380ca2eda31ab274e16508605ce204dfb0115c3c', 'apps/backend/app/ports/screenshot_answer.py': '059ef14896ddabd27e53e666c3a50803c07ebf2ad6b40a978dc18c2376fa76a5', 'apps/backend/app/ports/storage.py': '0f22c3e5cd4ee663bca51d27a0e6996916e2eda7753dbe2cc83885b99db2daaf', 'apps/backend/app/ports/streaming.py': 'e279618d9f6633ee0158189e2998af39cd2cf5376d64fb2b8b03c86728a1dfc3', 'apps/backend/app/ports/web_search.py': 'ddbfd4f25ad93f4b1749c7afe0854c2c8e16b819105e9d217a2adc2449af15b6', 'apps/backend/app/schemas/admin.py': 'b0e457bc772f52b4840d193ff47fdac5763e19e239920da15b13fc7137bd9ae2', 'apps/backend/app/schemas/authentication.py': '0d348dca673388e7c3205be1f0fbefdf7894da3e9f86751924ef2580d891e4e2', 'apps/backend/app/schemas/cn_resume_optimizer.py': '5840f641715ab56b7a78989fb9e60a5a4cbd183bdf4a2c97c756d100ce8dcfe0', 'apps/backend/app/schemas/document_processing.py': '47f21b25c4d20275cf10358a833f6a2324e095a1bc8d22e7971872aa54283d8f', 'apps/backend/app/schemas/document_service.py': '262fcb80a526a145129cd73e695901263e52b1ade1e37e650525b99f4058ee92', 'apps/backend/app/schemas/foundation.py': '5d04614e9e931e878284584e09c4d3f6d44496ab61a4b73400c13a422c308b59', 'apps/backend/app/schemas/live_answer.py': '271e08ea11becc48683cc690eeea9fbd1269187016135359906d9918063bfda3', 'apps/backend/app/schemas/material_upload.py': '192f76c59c4198cc8cc81d5ed27cba6acde25ba8895754d53899d21489b4cf46', 'apps/backend/app/schemas/mock_interview.py': '86db9960d73f812052b1ac0c80718e32db57a16f3a67ca68c1379d4967d36eb9', 'apps/backend/app/schemas/promotion.py': 'abe09ade5f33356c2d8fcaba29cdf3e3e5aa451bbb437563f78378c3f1afd3c0', 'apps/backend/app/schemas/realtime_speech.py': '5e5dfa1f3e612aaec8603aaa477ab6483244705e9fbb15ab60d714933691c46a', 'apps/backend/app/schemas/retrieval.py': '7cc3de63416e71987486ac6f123f78749b830308c03f91b77546cd6c5c4e1618', 'apps/backend/app/schemas/screenshot_answer.py': 'a242fa5f707f07d2d26573f888451981c4e159ab0158625f4927b6f94dc09d22', 'apps/backend/app/schemas/session.py': '60bc974b1fc0b0a933931f34f6d22887648a88a9367d5f84c040fa3ddf76a45f', 'apps/backend/app/services/._web_search_gateway.py': '59e018b5446ecdfefd1f271135abc85988aecf31e17c29b9d0db23bd208ae530', 'apps/backend/app/services/__init__.py': '5384bfdb2df380b6557cc7a71d16891415bccaa87699406e236f752c6415389f', 'apps/backend/app/services/admin_analytics.py': 'fceb02206cc944fabc40c3cf7e377e6cca5729f9f9f9fb253e0a8af37e2a5c41', 'apps/backend/app/services/admin_analytics_job.py': '89477b1dc881b772fe27815dd344362b3eff46eceff95b08ce849b2c9d6e045b', 'apps/backend/app/services/admin_bootstrap.py': 'e48f1d13b57cae3f89e20923f5bf21885398fd80d623b6eb30afea4c0cc8aa33', 'apps/backend/app/services/admin_capacity.py': 'c19b72df52909fb1aa5e4845644aee9c263260b16f78115b5997a5dffd21e385', 'apps/backend/app/services/admin_repository.py': '8f5d8eadede8fbf96befc3764b4bf958deacb91691dba9db6b737896dbde5535', 'apps/backend/app/services/admin_service.py': 'e67ab97785ad6de4f43047151b7199259102901582839288ab4fdee3419a78fa', 'apps/backend/app/services/alipay_provider.py': '68dc6bd82a9f1b4347519c3b2cb14692cbf756cb7fad3e3e8b5896dd53f6f359', 'apps/backend/app/services/authentication_repository.py': 'af096a9eed91d0f46e3dd4255a539a3104ede9d50d7d71b40fbf72c128b3cd57', 'apps/backend/app/services/authentication_service.py': '56de5d0f059231592ada21eae723978e3d9cdc4a83a3fdeb0bd1089d035605ff', 'apps/backend/app/services/billing_service.py': 'a95b5cda1ab436956f43c8700ef5b7f985946538306398d6d22aaf987ee39db4', 'apps/backend/app/services/chat_repository.py': '431180e0ea8fa847fc1e30b4ae591e1efb7d57efd182d197c676d1980f74e52f', 'apps/backend/app/services/chat_service.py': '8828c29018a1095899c7409123ab93dea33a00213fc58a51bd6afbf0e9ebe8cd', 'apps/backend/app/services/cn_provider_close_executor.py': 'ac7118182956e8dfd9bb622323282ed6d1a625ac3bebb9384545ccf669a1dea7', 'apps/backend/app/services/cn_realtime_entity_state.py': 'dff3963af27f4f5347e447304f983e0bd687d69c3dda8fded702bf8ea9c1be2a', 'apps/backend/app/services/cn_realtime_io_executor.py': '2e109eac1f73ab00e0f39ea5fcf40481560ebeaa8e368ef7f083667e78c4452e', 'apps/backend/app/services/cn_resume_optimizer_diagnostics.py': '0748bc7a8cdc05f31ba6184e22196da668e5f839a45137ee62ac2fb792f465ea', 'apps/backend/app/services/cn_resume_optimizer_provider.py': '92df5298dccbc13473a11ee51a5042b4e8629bf14a157371cf75e6ee1553609b', 'apps/backend/app/services/cn_resume_optimizer_repository.py': '776afded212d7522c676f2731af958ebff17160d90cd4cf841e55a29baa7ad03', 'apps/backend/app/services/cn_resume_optimizer_service.py': '901a388e78398f4a874dc0f1e836f80115c6959aa517216686240d3a0799ee5e', 'apps/backend/app/services/cn_resume_optimizer_source.py': '6c61e9e62f0eca699261ca95db0ebf920b7d28e70acc48b673035149223324bc', 'apps/backend/app/services/commercial_hardening.py': 'd0880f32765f5fab6e533dd80002032dc43e483bb86698d3a0ef3ed5c54d5d63', 'apps/backend/app/services/commercial_worker.py': '47663b6eda68ad61bf6422347e76292f1bc7c65dde00878df1424ece9ae31fdb', 'apps/backend/app/services/dashscope_realtime_asr_gateway.py': 'a768ea8a59a95208bf8389e62a50fc032af7be3a63d4d33416bd88433ce091ce', 'apps/backend/app/services/dashscope_task_asr_gateway.py': 'e3f729088a99ead9a79069e1d35712e2b5b7f62429b9272ce9fbd07cbd525f46', 'apps/backend/app/services/document_parser.py': '0d6c192bd471643f66921cf33a0541718cee0c8eb0647a6bd45b50ff57962015', 'apps/backend/app/services/document_processing.py': '233b064cfc70d2cb4289eb65328e1ae247d687871d13a4e23bb2ae53bbb5951e', 'apps/backend/app/services/document_processing_adapters.py': '8fa749eac4871b1601f2671419a6e11fce97136a8b464ebedc1e7a2175509e2f', 'apps/backend/app/services/document_processing_repository.py': '3d2d852638cf754fc2c615266e411937884d70d014f98ef29f081270f520fca1', 'apps/backend/app/services/document_repository.py': 'ae455d34d8caa79014b72e40f1e3b9787e852ffe5ec6ad89b623a7b0aa697435', 'apps/backend/app/services/document_service.py': 'ee128fd11c1aa85d6acf2e5d71a034873526a106ec62f6a1be370ca26e6ca527', 'apps/backend/app/services/embedding_pipeline.py': 'f4bd8db3fe67e690fbdaf9b91d7c0e7d907e064d7f288e2ec6114ada3a37aa7e', 'apps/backend/app/services/end_to_end_integration.py': '937eab572940366af5350b925ed10c0e59ff5857d68f832596c6359699c0d564', 'apps/backend/app/services/integration_verification.py': '297243b64be13a8656ad82e1de4568089f977c709cb8a7bd323c28b0fe9f6454', 'apps/backend/app/services/interview_session_repository.py': 'f1f1bb9fc2cb74c84c42415d81614c217253acb617bbc945b542fb84e57ba9bc', 'apps/backend/app/services/knowledge_index_quote.py': 'a44ffe259837e79c8271bf0c6040b28a7c89d6db3f8b759becee2c542eceb12e', 'apps/backend/app/services/knowledge_retrieval.py': '6723f825f64b948d8adfcc50a25301d7782b3b099d3a8cca4268f3fd151ccbfe', 'apps/backend/app/services/live_answer_stream_executor.py': '7bace4fc81f42f4b48744b84f9e607d90c0e8f929c37c23f5a44cbaf139c9bcd', 'apps/backend/app/services/material_availability.py': '4cdc4729e511031cc4c71cb7b23dfebd1f418c305632c20b9962356ae578a95f', 'apps/backend/app/services/material_deletion.py': '4910e2d07c4e4f2855df18b6cdccf69e1d3b73b61d0cd80575d68ebc24b955db', 'apps/backend/app/services/material_ingestion.py': 'a0361c311c2585bb45eae1087818efed62a8c77362f3aec04bda3dd822216fc8', 'apps/backend/app/services/material_object_keys.py': '4592d6b8d1093a3617ccacba2128109ca75ba50ea3df98bf6e707452b6234075', 'apps/backend/app/services/mock_interview_audio.py': '1039d5612ee2bf822351286238bfffa9e17d0519997410e8c497366716c8e830', 'apps/backend/app/services/mock_interview_diagnostics.py': '910143942163c4b903e2bb80440af18133d02575106d2d0d756c0209788d1cc8', 'apps/backend/app/services/mock_interview_generation.py': 'a31f0a072ecabc97ae12387123296b6c8abbf320c25cd25544bc0777a8cddd66', 'apps/backend/app/services/mock_interview_jobs.py': 'fb9f39fab6b8de5a0100dd29aff79cee6aea0af445b70d64b3a7b93c0141b970', 'apps/backend/app/services/mock_interview_legacy.py': '97a5846395a631617339ee8a433431ab939e53d88dd73f5bde5a02b881c53f9f', 'apps/backend/app/services/mock_interview_repository.py': 'f769ece3b35b1323011d828f96eb4e094abef424094e3e1c28fc544c385480cf', 'apps/backend/app/services/mock_interview_rounds.py': 'b7990c8bcbc33c651ab444379e078e28bb056cdb4ff91ad545d2644221bb1afd', 'apps/backend/app/services/mock_interview_runtime.py': '9639e10f5a9be34b0cae44cd8ad9e2972aba196fd88a3972782c7acd481784d5', 'apps/backend/app/services/mock_interview_tts.py': '38e6540b7b05c7f91728a7e0284e21dce95b8f30f5c12e15cda09d760290acea', 'apps/backend/app/services/mzfpay_provider.py': '9c2ad8e3447af2aa5f3caaee35ed3ac432e595a3510aa9980979c5246dbb2b1e', 'apps/backend/app/services/partner_program.py': '4eae767a3e5696d864c0f45b069c53177996d51d72d600b0376f3c5911bfd543', 'apps/backend/app/services/payment_channel_service.py': 'a2e8f5d6bd7e395a259d8fe9b2aac5ce532b7f6a138210b0e72f9a9df35dd693', 'apps/backend/app/services/payment_reconciliation.py': '484c28ebfa762370898695f27e4d33577a1b9e1b381c0039d9ead3c6a445e24b', 'apps/backend/app/services/postgres_authentication_repository.py': 'f6f2d560041e9e8d058aee6c6b1f4fa7cf94bf7ebd34f0f5f54be31889fedcbf', 'apps/backend/app/services/postgres_billing_repository.py': 'a85a69221334c4f45c62fc9971fd5cfb4d6235e8e1ec01b48aed99bb937d035a', 'apps/backend/app/services/postgres_interview_session_repository.py': '611260aaee7571d818e7771e166ea48c48b0d8d68b21ed6efd537a0244d542f9', 'apps/backend/app/services/postgres_material_persistence.py': '6bc75c3286d2bc9747c8178404818c6ec3b67681a0e3db5f02d457786d384601', 'apps/backend/app/services/postgres_migrations.py': 'b372b42696c9acf7a7b7672b5202f3dc95bc4bb69e44e51125617156501c713d', 'apps/backend/app/services/postgres_points_redemption_repository.py': '20ff35a5ad8b966b5e6a20e5ced4ceafc3a7277de5a76b5b250aacecd28a6b2b', 'apps/backend/app/services/programming_prompt.py': '31d8c67a0f221ca382d7a6eafac64b699a05c62f6da238dc54bd64e8707bf593', 'apps/backend/app/services/promotion_analytics_job.py': 'dc215318a85cd783351e1dfdf19f0a2aa240ada4fdf722f2bf494c42d484c8f9', 'apps/backend/app/services/promotion_repository.py': '7cfec5bb9e84282d01623fe65ec53302103e5137f0290a2c1d05fe50db7c88ad', 'apps/backend/app/services/question_prefetch_scheduler.py': '36bc5ab7fc2329945a3becdedc0ccc0a38356c334e8b32a735610c58774d744f', 'apps/backend/app/services/realtime_control_executor.py': '49258e90349e5fb32682e26fc75ef1833aca5214824ef00430e9d7b6d70a0430', 'apps/backend/app/services/realtime_event_wait.py': 'b6146abf4db5035eb4352575eb61a7bd8b9c1ba01eb55968fd258753d964c7c4', 'apps/backend/app/services/realtime_speech_repository.py': '886f6aa4148f5a36d1f5c5748224db4b7cc217a4a5b542fd476efbd2f4fd0857', 'apps/backend/app/services/realtime_speech_service.py': '4c4ec7ec5a59f48d2ec1386e15b9361cd80b4f66d30f0e77edc7955ec6c5b2c2', 'apps/backend/app/services/redis_live_task_repositories.py': 'f20ecb44738396f17a8863c7f6844e686cacdc4812a136e1ca4562dede67159f', 'apps/backend/app/services/redis_realtime_speech_repository.py': '013e73f55215958cbe8bff952edd53612cccf65ee40e9b6be9b7439eac7967a5', 'apps/backend/app/services/resume_optimizer_export.py': 'ee7d2ea06403d44b7c05658b9e349696bded4ddadc688fca5a977cb8a497096d', 'apps/backend/app/services/screenshot_answer_performance.py': '8d4d0d6263699779adc7bf6b857c7bf2cb8f56f136e6b0f0b1bf1c431e95ff66', 'apps/backend/app/services/screenshot_answer_repository.py': '16df19c0a595621cfa84847f48867798b03da83501e706f03b9881a073b99219', 'apps/backend/app/services/screenshot_answer_service.py': 'd2963699f8d33b94077d4651ce7a6f166fc98940f4b9a39562c1c4cb2a5bf69a', 'apps/backend/app/services/screenshot_stream_admission.py': '6467fabb6675f5483430750571442194dfbd8621363601ceb810e6bf3cfbf7f2', 'apps/backend/app/services/session_mode_guard.py': 'cbb726b645d8ed82af93fa63362706f970ff63e1bb8392d162d73d883a45eeab', 'apps/backend/app/services/session_service.py': '07207302764ca76c0cb1e153b90ba38085950b77f8d0a1b60de75b265925a42c', 'apps/backend/app/services/sms_verification_provider.py': '8a8c2a19f0fa0d6ee30239f3ac56164963661998d1bb68466032946894319ce3', 'apps/backend/app/services/upload_intent_repository.py': '5ca514b3f11f0668cf82325c819e11d6b1710ef0557a35729f144d723fab964e', 'apps/backend/app/services/web_search_gateway.py': 'e382df112b85708e571849ad1d518c4cee63a917099a6632395acef7158db997', 'apps/backend/app/services/wechat_pay_provider.py': '8a9bec3579d972662b8dd57ec61afb8a9abec9b60c4a7cac80fa4cd927637963', 'apps/backend/app/worker.py': '799f884210678a62648b647927357c52224b5db3852d46fe438e604b8b4ee6f3', 'apps/backend/migrations/README.md': '1ab4b68abb9b0c5418d351399cd07430d738779156adbd150453bf0cf4112475', 'apps/backend/migrations/versions/0001_document_service_metadata.sql': '3892ad4085548d788ba253992ebe1adfac2ae24619ebd75b836aa309c372d9bc', 'apps/backend/migrations/versions/0002_document_processing_pipeline.sql': '4be9e56adf2afb60a2546578584b8972216349ab7aa9ffc60258d29ed4a16a06', 'apps/backend/migrations/versions/0003_commercial_material_rag_persistence.sql': 'e2d83184eb6f23804b0484452a41256ed5fa11d279b88c2a150cb8745eabfc5b', 'apps/backend/migrations/versions/0004_interview_session_persistence.sql': '3e73be86ad70284d6b164f678375b6e003f077eed476e509377ac6272efb4ef3', 'apps/backend/migrations/versions/0005_commercial_architecture_hardening.sql': 'bd2e2fe76d8c2d2b091f1befa836a28e5f6d38b74e29ca9c32c19992e8e8c57b', 'apps/backend/migrations/versions/0006_sms_authentication_service.sql': '6309d78762ac28d93246d26470381d8f3212c890e46861845e6f88a9c3683408', 'apps/backend/migrations/versions/0007_realtime_interview_runtime.sql': 'fe6c0365d7fc4fe519d1bd6238770da6f6e56ed25d4d6922038b2258c3abfd3b', 'apps/backend/migrations/versions/0008_persistent_points_redemption.sql': '784ca0852c587c51a87dda6b8ec9635a149afebbd39ac07e4f900f8a6e3eb926', 'apps/backend/migrations/versions/0009_commercial_billing_persistence.sql': '381369cf69684be492dafc43dbd9ec2acb8093ff353a0eb638b956221d6336c0', 'apps/backend/migrations/versions/0010_payment_recovery_reconciliation.sql': 'c442714fa4c76f58623a59f046e40bec1afa91404280b0cc3f675c468083824b', 'apps/backend/migrations/versions/0011_enable_pgvector_extension.sql': 'f5da00a0e65224732b53a62c2e87bfbb3066d6a4f801a0eddd4fb20df274c158', 'apps/backend/migrations/versions/0012_billable_interview_usage.sql': '773af13216ed2fe8571e6d4f3c688291befe5a494bdf2c54cb6c314e62ad8681', 'apps/backend/migrations/versions/0013_official_alipay_payments.sql': 'c2a9f57d921f82bf65a38274123f48c635f7d69f875d814d167c3c7741b3434e', 'apps/backend/migrations/versions/0014_commercial_admin_console.sql': '70b7d1a181a1a0fbaeae5a8ca7cfc45c439c80bfecc8198bffe6477cda8aabcb', 'apps/backend/migrations/versions/0015_admin_redemption_batches.sql': 'e4b58c285276c7fd26cd37d31f258b61fc7e06eeee2112d0fb6b0a4876399096', 'apps/backend/migrations/versions/0016_idle_interview_lifecycle.sql': '3cf0d238accade6fa0f4df3de3e3e7ca4a529515e10fe0c730f61b4ae2274163', 'apps/backend/migrations/versions/0017_admin_operations_analytics.sql': '72d6a8ce666c57d335b3cdd1c71697be18e4e29fa7fe29a7adf93938a6d1ca0e', 'apps/backend/migrations/versions/0018_admin_managed_billing_catalog.sql': '5f2ccce0657dd9fd2493712efa60dfabff1ed8b0bc2cfd9c116788ce3a25e61f', 'apps/backend/migrations/versions/0019_admin_payment_channels.sql': 'b96d4ab7546fac4fa2dca2ad40f90bbe207f13bba5286ebd84f2a5c676e59cc7', 'apps/backend/migrations/versions/0020_admin_payment_diagnostics.sql': 'ab4797a233f61081d0abac7b1e7cc4ebf1dd02d3a378658984e35700e17bdd98', 'apps/backend/migrations/versions/0021_referral_rewards.sql': 'edd873cb2caef7e927badceac2ecb4b5f7eeca31b1b2dc7bd7bc5ac8eba855ab', 'apps/backend/migrations/versions/0022_referral_ledger_constraint_repair.sql': '40c4672fef8b6eea3475430ce06dc57160dd91560d99f5c2cb380bab2ad34f16', 'apps/backend/migrations/versions/0023_stale_usage_reservation_recovery.sql': '0237023caa33aad2c2aadd897ef14ffba7a71d8c53dcc39a61693512c14c77a0', 'apps/backend/migrations/versions/0024_ai_runtime_performance_metrics.sql': 'fb524a3615dde8655ac275edbe5865c96ab9513b2054d1cb0cb4e32476ff14f0', 'apps/backend/migrations/versions/0025_referral_ledger_constraint_repair_v2.sql': '596f8facb0ee00474224f988ab0e5d5b9c0b052d7bbf3975639824019092731d', 'apps/backend/migrations/versions/0026_knowledge_collection_lifecycle.sql': 'be4e9dfb2829ef12ddf64be80d8939e1bcbba5d6ee84adc12d56d31ee0200214', 'apps/backend/migrations/versions/0027_knowledge_index_billing_sources.sql': '9e18957183f2f5394ddfd5035a7c54a50569f9fee4339222201ae8ac63e2b4bf', 'apps/backend/migrations/versions/0028_restore_unstarted_interviews.sql': '62ddf496b18553329f4ea8f892826a82e4c7f98aab79fb037c5dfb11f1342cf3', 'apps/backend/migrations/versions/0029_early_referral_mutual_rewards.sql': 'bbf7a2532d23fd92da4f03cba9dca9e34d698a16bfde6db9b3357814c2b791fa', 'apps/backend/migrations/versions/0030_dysmsapi_code_digest.sql': 'c2e98bebf654acf5e741e43a7e15e03458fb8eebf2f5666fdd826fab9e3a0e64', 'apps/backend/migrations/versions/0031_capacity_metric_granularity.sql': '0eae54a3a627654486d9de281df079f23823b922f45aa185cd688aa0bc009c9e', 'apps/backend/migrations/versions/0032_realtime_minute_billing.sql': '6f28d32929478f0a0ff649b0949cefeed7a0df5cf6ba6e1ff2ec809dca11385d', 'apps/backend/migrations/versions/0033_interview_language.sql': '43c4dbee6084f86dea70b156f44d8a676c467b98c0501db2f029370332529377', 'apps/backend/migrations/versions/0034_interview_programming_preference.sql': '8f6875500b0d066c826fc3fd5a5c0c7be6368d86d33d5fed31d904e20dcee072', 'apps/backend/migrations/versions/0035_session_auto_answer.sql': '489b637fa188a5d05a4d03ea6a67b9840dd1e6f2c18010eb14f1f2c5eb1a6109', 'apps/backend/migrations/versions/0036_written_exam_mode.sql': 'ca1065f98d2e827adfb44095eafda739b137bdef7895180cb309bad9235a2887', 'apps/backend/migrations/versions/0037_written_exam_billing_constraints.sql': '2267d05c9067a2acc7cf6b0bcf2794c654b9503d68fee147b3b53abbc744a0da', 'apps/backend/migrations/versions/0038_promotion_center.sql': '0a289302e44b0e1140ce1801773cc8cb325180f6f2d0c14c22b0e3b5ced70d21', 'apps/backend/migrations/versions/0039_partner_program.sql': '1566eac610f094acf482308e09b301ba1e4571f67f0fdd88eee8b2c17798dc6f', 'apps/backend/migrations/versions/0040_partner_payout_operations.sql': '6c13dee98da4c45a6adfcbc8628d6c357ffba2814ddf2d5398cb8e59aae56aae', 'apps/backend/migrations/versions/0042_partner_program_activity_settings.sql': '1ea93e8677a5c0674248fdf730161632e10207a94893e2cc357aa0e839d729a9', 'apps/backend/migrations/versions/0044_durable_material_processing.sql': '800208f15ed82feb07bc21233893e8ad7b55901653c2c86a597fd258e30b7105', 'apps/backend/migrations/versions/0049_interview_audio_mode.sql': '8ebbfb9a7f5803d617df51ba6f474326281de9775d12b5360484dbd0f9e4b4b0', 'apps/backend/migrations/versions/0050_web_answer_billing.sql': 'b6ee5182f25ba77bfd1979bc6920bc3a39064a50a870d31ccfbd89f2e6d5bd9a', 'apps/backend/migrations/versions/0051_mock_interviews.sql': 'ee554bdba7b0f67d5df836a0d2e167168470c88847663442e6b1f7705f4bcd26', 'apps/backend/migrations/versions/0054_cn_resume_optimizer.sql': '7fe56ad0082323ea440640e2c7303305f38c22d1704bc04f94a123d4922705e7', 'apps/backend/migrations/versions/README.md': '628633961730735d9332c17124da529a66ae527b2684dd5bc5191ab0b0239763', 'apps/backend/pyproject.toml': 'ac83f87d44f6d8faff2186de8edab3a830fde2dfaab42cb891111c7df50cf2de'}, 'python': '3.13.15', 'dependencies': {'PyJWT': '2.13.0', 'aliyun-python-sdk-core': '2.16.1', 'aliyun-python-sdk-kms': '2.16.5', 'annotated-doc': '0.0.5', 'annotated-types': '0.8.0', 'anyio': '4.14.2', 'certifi': '2026.7.22', 'cffi': '2.1.1', 'charset-normalizer': '3.5.1', 'click': '8.5.0', 'crcmod': '1.7', 'cryptography': '50.0.1', 'fastapi': '0.141.1', 'h11': '0.16.0', 'httpcore': '1.0.9', 'httpx': '0.28.1', 'idna': '3.19', 'jmespath': '1.1.0', 'offersteady-backend': '0.1.0', 'oss2': '2.19.1', 'pillow': '12.3.0', 'pip': '26.2.1', 'psycopg': '3.3.5', 'psycopg-binary': '3.3.5', 'psycopg-pool': '3.3.3', 'pycparser': '3.0', 'pycryptodome': '3.23.0', 'pydantic': '2.13.5', 'pydantic-settings': '2.15.0', 'pydantic_core': '2.46.5', 'python-dotenv': '1.2.3', 'python-multipart': '0.0.32', 'python-socks': '3.0.0', 'redis': '8.1.0', 'reportlab': '4.4.9', 'requests': '2.34.2', 'six': '1.17.0', 'starlette': '1.6.0', 'typing-inspection': '0.4.4', 'typing_extensions': '4.16.0', 'urllib3': '2.7.0', 'uvicorn': '0.52.4', 'websocket-client': '1.9.2', 'websockets': '17.1'}, 'settingsSha256': '4ba6de09bcb1151c047121df981d087be4b186ccb332ea17e5426a205c8e94d9', 'openapiSha256': 'dd7da7440bf0177b590396cf09253219eac1b6bf786e98f9fd0ce4bcf8eee272', 'httpPaths': 203, 'ancillary': {'packages/protocol/src/material-upload-formats.json': 'e6607164d21950319ab2b6179d38ed6cf771715a2663c18db704af612907ac2f'}}

sys.dont_write_bytecode = True
WORKERS = []
OWNER, SESSION, DEVICE, CODE = ("synthetic-probe-owner", "synthetic-probe-session",
    "synthetic-probe-device", "000000")
NOW = 1_800_000_000_000
ANCILLARY_PATH = "packages/protocol/src/material-upload-formats.json"
DESKTOP_MANIFEST_SHA256 = "6cb2a0e01afa7c8539a1cccdb1f0d0c8dd1907304ffe71711438ae6b70061340"


class ProbeError(RuntimeError):
    pass


def require(value, code):
    if not value:
        raise ProbeError(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def serialize(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def deny(*args, **kwargs):
    raise ProbeError("external_io_forbidden")


def install_guards():
    def audit(event, args):
        if event in {"subprocess.Popen", "os.system", "os.fork", "os.forkpty", "os.posix_spawn",
            "socket.connect", "socket.getaddrinfo", "socket.sendto", "sqlite3.connect", "os.mkdir",
            "os.rename", "os.remove", "os.rmdir", "os.chmod", "os.chown", "os.utime",
            "os.link", "os.symlink", "os.truncate"}:
            deny()
        if event == "open" and len(args) >= 3 and isinstance(args[2], int):
            if args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                deny()
    sys.addaudithook(audit)
    socket.socket.connect = socket.socket.connect_ex = deny
    socket.create_connection = socket.getaddrinfo = deny
    original_start = threading.Thread.start
    def tracked_start(worker, *args, **kwargs):
        require(worker.name.startswith(("synthetic-cn-shared-probe", "realtime-control",
            "cn-realtime-ingress", "cn-realtime-lifecycle", "cn-realtime-preparation", "cn-provider-close"))
            or getattr(getattr(worker, "_target", None), "__name__", None) == "_do_shutdown",
            "unapproved_worker_thread")
        WORKERS.append(worker)
        return original_start(worker, *args, **kwargs)
    threading.Thread.start = tracked_start
    import psycopg
    psycopg.connect = psycopg.Connection.connect = psycopg.AsyncConnection.connect = deny


def verify_source(root, expected):
    """Only read/compile inputs. Ancillary SHA must come from the actual baseline.

    The ancillary JSON was outside the original 233-input capture; accepting its
    absence or silently substituting a local checkout would hide image drift.
    """
    actual = {p.relative_to(root).as_posix(): sha(p.read_bytes())
        for directory in ("apps/backend/app", "ai/prompts", "apps/backend/migrations")
        for p in (root / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts
        and p.suffix != ".pyc" and p.name != ".desktop-release-manifest.lock"}
    actual["apps/backend/pyproject.toml"] = sha((root / "apps/backend/pyproject.toml").read_bytes())
    require(actual == expected["inventory"] and len(actual) == 238, "application_inventory_mismatch")
    compiled = 0
    for path in (root / "apps/backend/app").rglob("*.py"):
        if not path.name.startswith("._"):
            compile(path.read_bytes(), str(path), "exec"); compiled += 1
    require(compiled == 162, "compiled_python_count_changed")
    ancillary = expected.get("ancillary")
    require(isinstance(ancillary, dict) and set(ancillary) == {ANCILLARY_PATH}
        and re.fullmatch(r"[0-9a-f]{64}", str(ancillary[ANCILLARY_PATH])) is not None,
        "baseline_ancillary_expectation_missing")
    path = root / ANCILLARY_PATH
    require(path.is_file() and sha(path.read_bytes()) == ancillary[ANCILLARY_PATH],
        "baseline_ancillary_mismatch")
    manifest_path = root / "apps/backend/app/desktop_release_manifest.json"
    require(sha(manifest_path.read_bytes()) == DESKTOP_MANIFEST_SHA256,
        "companion_release_manifest_changed")
    manifest = json.loads(manifest_path.read_bytes())
    require(len(manifest["entries"]) == 6 and {entry["version"] for entry in manifest["entries"]} == {"1.3.6", "2.0.0"},
        "companion_release_version_changed")
    return actual, compiled


def forbid_lifespan(application):
    application.router.lifespan_context = deny
    application.router.startup = deny


def fixture(settings, *, edition="cn"):
    from app.ports.interview_session import SessionBoundDocument
    from app.ports.realtime_speech import DesktopDeviceRecord, SessionDesktopBindingRecord
    from app.services.interview_session_repository import InMemoryInterviewSessionRepository
    from app.services.realtime_speech_service import RealtimeSpeechService
    from app.services.session_service import SessionService
    repository = InMemoryInterviewSessionRepository()
    documents = Mock()
    documents.get_by_id.return_value = None
    selected = settings.model_copy(update={"product_edition": edition})
    sessions = SessionService(settings=selected, repository=repository, document_repository=documents)
    record = sessions.create_session(user_id=OWNER, title="Synthetic device status")
    record = replace(record, session_id=SESSION, status="live", material_binding=replace(
        record.material_binding, session_id=SESSION, bound_documents=[SessionBoundDocument(
            document_id=f"synthetic-material-{i}", document_kind="knowledge", display_name="Synthetic",
            status="ready") for i in range(12)]))
    repository.sessions = {SESSION: record}
    repository.get_session = Mock(wraps=repository.get_session)
    repository.get_control_state = Mock(wraps=repository.get_control_state)
    repository.save_session = Mock(wraps=repository.save_session)
    device = DesktopDeviceRecord(device_id=DEVICE, manual_code=CODE, display_name="Synthetic desktop",
        capabilities={}, registered_at_ms=NOW, last_seen_at_ms=NOW)
    binding = SessionDesktopBindingRecord(binding_id="synthetic-probe-binding", session_id=SESSION,
        owner_user_id=OWNER, device_id=DEVICE, manual_code=CODE, display_name="Synthetic desktop",
        capabilities={}, bound_at_ms=NOW, last_seen_at_ms=NOW)
    state = SimpleNamespace(device=device, binding=binding, fallback=False)
    def lookup(*, device_id, manual_code):
        return state.binding if not state.fallback else None
    events = Mock(side_effect=lambda event: event)
    service = object.__new__(RealtimeSpeechService)
    service.settings, service.session_service = selected, sessions
    service.repository = SimpleNamespace(get_desktop_device_by_code=lambda code: state.device,
        get_latest_session_desktop_binding_for_device=Mock(side_effect=lookup),
        get_latest_session_desktop_binding_by_code=Mock(side_effect=lambda **_: state.binding),
        save_event=events)
    return SimpleNamespace(service=service, sessions=sessions, repository=repository,
        documents=documents, record=record, state=state, events=events)


async def invoke(target, request, *, manual=True, session_id=SESSION, user_id=None, device_id=DEVICE):
    from app.modules.realtime_speech import publish_device_status
    from app.ports.authentication import AuthenticatedRequestContext
    from app.schemas.realtime_speech import RealtimeDeviceStatusRequest
    command = RealtimeDeviceStatusRequest(deviceId=device_id, captureState="ready", userId=user_id,
        manualCode=CODE if manual else None, sourceHealth=[{"sourceId": "synthetic-private-source",
            "label": "synthetic-private-content" * 10, "level": .2, "privateExtra": "must-filter"}],
        capabilities={"platform": "synthetic", "appVersion": "1.3.6", "privateExtra": "must-filter"})
    auth = None if manual else AuthenticatedRequestContext(OWNER, "synthetic-login", "synthetic-auth")
    return await publish_device_status(session_id, request, command, auth, target.service)


async def expect_error(call, status, error_code=None):
    from app.core.errors import DomainRequestError
    try:
        await call
    except DomainRequestError as error:
        require(error.status_code == status and (error_code is None or error.error_code == error_code),
            "synthetic_error_contract_changed")
    else:
        raise ProbeError("synthetic_invalid_status_authorized")


def require_lightweight(target, *, controls, events):
    require(target.repository.get_control_state.call_count == controls
        and target.repository.get_session.call_count == 0
        and target.documents.get_by_id.call_count == 0
        and target.repository.save_session.call_count == 0
        and target.events.call_count == events, "device_status_read_or_event_contract_changed")


async def synthetic_device_status(settings, request, executor):
    from app.platform import cn_device_status_timing as timing
    from app.core.logging import configure_logging
    samples = []
    class Capture(logging.Handler):
        def emit(self, record):
            samples.append(record.getMessage())
    logger = configure_logging(settings.model_copy(update={"log_level": "INFO"}))
    original = (logger.handlers[:], logger.level, logger.propagate)
    logger.handlers = [Capture()]; logger.propagate = False
    try:
        require(timing._logger.isEnabledFor(logging.INFO), "timing_logger_not_configured")
        timing._sample_counter = 19
        target = fixture(settings)
        result = await invoke(target, request)
        require(result.success and result.data["kind"] == "device-status", "device_status_event_missing")
        payload = result.data["payload"]
        require(payload["deviceId"] == DEVICE and payload["captureState"] == "ready"
            and len(payload["sourceHealth"][0]["label"]) == 120
            and "privateExtra" not in payload["sourceHealth"][0]
            and "privateExtra" not in payload["capabilities"], "device_status_payload_changed")
        require_lightweight(target, controls=2, events=1)
        require(len(samples) == 1 and samples[0].startswith("cn_device_status_timing "), "timing_sample_missing")
        sample = json.loads(samples[0].split(" ", 1)[1])
        labels = {"schema", "sample_every", "queue_ms", "work_ms", "worker_failed"} | {
            f"{phase}_{suffix}" for phase in timing._PHASES for suffix in ("ms", "count")}
        require(set(sample) == labels and all(type(v) in (int, float) and isfinite(v) and v >= 0
            for v in sample.values()) and sample["binding_repository_count"] == 2
            and sample["event_repository_count"] == 1, "timing_sample_fields_changed")
        require(all(marker not in samples[0] for marker in (OWNER, SESSION, DEVICE, CODE,
            "synthetic-private", "must-filter")), "timing_private_content_leaked")
        require(await executor.run(lambda: timing._current_trace.get()) is None, "timing_worker_scope_leaked")
        checked = 1
        for invalid in ("generation", "heartbeat", "owner", "missing", "replaced"):
            target = fixture(settings)
            if invalid == "generation": target.state.device = replace(target.state.device, generation=2)
            elif invalid == "heartbeat": target.state.device = replace(target.state.device,
                last_seen_at_ms=NOW - settings.realtime_desktop_heartbeat_ttl_seconds * 1000 - 1)
            elif invalid == "owner": target.state.binding = replace(target.state.binding, owner_user_id="synthetic-other")
            elif invalid == "missing": target.repository.sessions.clear()
            await expect_error(invoke(target, request, session_id="synthetic-replaced" if invalid == "replaced" else SESSION),
                410 if invalid == "replaced" else 404, "desktop_binding_replaced" if invalid == "replaced" else None)
            require(target.events.call_count == 0 and target.repository.get_session.call_count == 0
                and target.documents.get_by_id.call_count == 0, "invalid_status_saved_or_loaded_materials")
            checked += 1
        target = fixture(settings); target.state.fallback = True
        await invoke(target, request, device_id="synthetic-old-device")
        require(target.service.repository.get_latest_session_desktop_binding_for_device.call_count == 2
            and target.service.repository.get_latest_session_desktop_binding_by_code.call_count == 1,
            "binding_fallback_order_changed")
        require_lightweight(target, controls=2, events=1); checked += 1
        for change in ("ended", "deleted"):
            target = fixture(settings)
            original_read = target.sessions.get_control_state
            calls = 0
            def mutate_after_read(**kwargs):
                nonlocal calls
                calls += 1
                value = original_read(**kwargs)
                if calls == 1:
                    if change == "deleted": target.repository.sessions.clear()
                    else: target.repository.sessions[SESSION] = replace(target.record, status="ended")
                return value
            target.sessions.get_control_state = mutate_after_read
            if change == "deleted": await expect_error(invoke(target, request), 404)
            else: await invoke(target, request)
            require_lightweight(target, controls=2, events=int(change == "ended")); checked += 1
        target = fixture(settings)
        await invoke(target, request, manual=False)
        require_lightweight(target, controls=1, events=1)
        await expect_error(invoke(target, request, manual=False, user_id="synthetic-other"), 403)
        require_lightweight(target, controls=1, events=1); checked += 1
        timing._sample_counter = 19
        before = len(samples)
        target = fixture(settings, edition="global")
        await invoke(target, request)
        require(target.repository.get_session.call_count == 2 and target.repository.get_control_state.call_count == 0
            and target.documents.get_by_id.call_count > 0 and target.events.call_count == 1
            and len(samples) == before and timing._sample_counter == 19, "global_original_status_path_changed")
        return {"syntheticStatusCases": checked + 1, "controlReadsPerValidManualStatus": 2,
            "fullSessionReadsPerValidManualStatus": 0, "materialReadsPerValidManualStatus": 0,
            "eventsPerValidManualStatus": 1, "timingPrivacyPassed": True, "globalOriginalPathPassed": True}
    finally:
        logger.handlers, logger.level, logger.propagate = original


async def synthetic_loop_responsiveness(settings, request, executor):
    from app.platform import cn_device_status_timing as timing
    checked = 0
    for configured in (True, False):
        started, release = threading.Event(), threading.Event()
        target = fixture(settings)
        original = target.service.repository.get_desktop_device_by_code
        worker_ids = []
        def slow(code):
            worker_ids.append(threading.get_ident()); started.set()
            require(release.wait(3), "event_loop_could_not_release_slow_repository")
            return original(code)
        target.service.repository.get_desktop_device_by_code = slow
        request.app.state.realtime_control_executor = executor if configured else None
        # Select a non-sampled request to check the real modulo gate and avoid
        # incidental INFO on stdout; this does not replace the timing wrapper.
        timing._sample_counter = 0
        task = asyncio.create_task(invoke(target, request))
        try:
            async with asyncio.timeout(2):
                while not started.is_set(): await asyncio.sleep(.001)
            require(not task.done() and worker_ids[0] != threading.get_ident(), "sync_repository_blocked_event_loop")
            release.set()
            await asyncio.wait_for(task, 2)
            require_lightweight(target, controls=2, events=1)
            checked += 1
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
    request.app.state.realtime_control_executor = executor
    return checked


async def until(predicate, code):
    async with asyncio.timeout(2):
        while not predicate():
            await asyncio.sleep(.001)
    require(predicate(), code)


async def synthetic_voice_lanes(settings, request, control):
    from app.modules.realtime_speech import _disconnect_voice_publisher, _voice_io
    from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor
    executor = CnRealtimeIoExecutor()
    diag = executor.diagnostics()
    require((diag["ingress"]["configuredWorkers"], diag["ingress"]["configuredQueueMax"],
        diag["lifecycle"]["configuredWorkers"], diag["lifecycle"]["configuredQueueMax"]) == (4, 16, 2, 8),
        "cn_io_default_capacity_changed")
    checked = 0
    try:
        for configured in (True, False):
            entered, release = threading.Event(), threading.Event()
            calls = []
            def close(**kwargs):
                calls.append(threading.get_ident()); entered.set()
                require(release.wait(3), "synthetic_close_not_released")
            service = SimpleNamespace(settings=settings, disconnect_publisher=close)
            request.app.state.cn_realtime_io_executor = executor if configured else None
            task = asyncio.create_task(_disconnect_voice_publisher(request, service, token="synthetic-token"))
            try:
                await until(entered.is_set, "synthetic_close_not_started")
                require(not task.done() and len(calls) == 1 and calls[0] != threading.get_ident(),
                    "close_blocked_main_loop")
                require(await asyncio.wait_for(executor.run(lambda: 17, operation_name="ingest_frame"), 1) == 17
                    and await asyncio.wait_for(control.run(lambda: 19), 1) == 19,
                    "close_occupied_ingress_or_control_lane")
                release.set(); await asyncio.wait_for(task, 2)
                require(len(calls) == 1, "close_replayed")
                checked += 1
            finally:
                release.set(); await asyncio.gather(task, return_exceptions=True)
        # Global keeps the original direct call; it must not enter a CN pool.
        original = SimpleNamespace(settings=SimpleNamespace(product_edition="global"))
        identity = await _voice_io(request, original, threading.get_ident, operation_name="ingest_frame")
        require(identity == threading.get_ident(), "global_voice_dispatch_changed")
    finally:
        executor.shutdown()
        request.app.state.cn_realtime_io_executor = None
    return {"voiceNonblockingCases": checked, "voiceDefaultCapacityPassed": True,
        "slowCloseLeavesIngressAndControlAvailable": True, "globalVoiceDispatchUnchanged": True}


async def synthetic_cancel_and_shutdown():
    """Admitted resource cleanup survives cancellation/shutdown without expanding capacity."""
    from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor
    executor = CnRealtimeIoExecutor(ingress_workers=3, ingress_queue_max=0,
        lifecycle_workers=1, lifecycle_queue_max=0)
    entered, release, occupied, release_close = [], threading.Event(), threading.Event(), threading.Event()
    created, cleaned, forbidden = [], [], []
    def close():
        occupied.set(); require(release_close.wait(3), "synthetic_lane_not_released")
    def create(index):
        entered.append(index)
        require(release.wait(3), "synthetic_create_not_released")
        created.append(index); return index
    blocker = asyncio.create_task(executor.run(close, lane="lifecycle", operation_name="publisher_disconnect"))
    owners = [asyncio.create_task(executor.run(lambda i=i: create(i), operation_name="publisher_create",
        on_abandoned_result=lambda result: cleaned.append(result))) for i in range(3)]
    waiters = []
    try:
        await until(lambda: len(entered) == 3 and occupied.is_set(), "synthetic_owners_not_started")
        waiters = [asyncio.create_task(executor.run(lambda: forbidden.append(1), lane="lifecycle",
            operation_name="publisher_disconnect")) for _ in range(3)]
        await until(lambda: executor.diagnostics()["lifecycle"]["waiting"] == 3, "synthetic_waiters_not_started")
        for task in owners: task.cancel("synthetic-original-cancellation")
        await asyncio.sleep(0)
        executor.shutdown()
        for task in waiters: task.cancel()
        await asyncio.gather(*waiters, return_exceptions=True)
        release.set()
        await until(lambda: len(created) == 3, "synthetic_create_did_not_finish")
        await asyncio.sleep(.01)
        for task in owners: task.cancel()
        require(cleaned == [] and not any(task.done() for task in owners)
            and executor.diagnostics()["lifecycle"]["maxPending"] == 1,
            "shutdown_cleanup_capacity_expanded_or_skipped")
        release_close.set(); await blocker
        results = await asyncio.gather(*owners, return_exceptions=True)
        require(all(isinstance(value, asyncio.CancelledError) for value in results)
            and sorted(created) == sorted(cleaned) == [0, 1, 2] and not forbidden,
            "cancelled_creation_replayed_or_cleanup_lost")
        try:
            await executor.run(lambda: forbidden.append(1), operation_name="ingest_frame")
        except RuntimeError:
            pass
        else:
            raise ProbeError("closed_executor_accepted_new_business")
        await asyncio.sleep(0)
        final = executor.diagnostics()
        require(final["cleanupFailed"] == final["outstanding"] == 0 and final["poolsClosed"] == 1
            and final["lifecycle"]["maxPending"] == 1 and final["ingress"]["pending"] == 0
            and final["lifecycle"]["pending"] == 0, "shutdown_resource_or_capacity_contract_changed")
        return {"cancelledResourcesCreated": 3, "cancelledResourcesCleaned": 3,
            "shutdownRejectsNewBusiness": True, "shutdownCleanupCapacityPassed": True}
    finally:
        release.set(); release_close.set()
        await asyncio.gather(blocker, *owners, *waiters, return_exceptions=True)
        executor.shutdown()


def synthetic_metadata_and_modes(settings):
    from app.core.errors import DomainRequestError
    from app.ports.retrieval import RetrievalFilter, RetrievedChunk
    from app.services.knowledge_retrieval import KnowledgeRetrievalService
    from app.services.realtime_speech_service import RealtimeSpeechService
    from app.services.session_mode_guard import require_standard_session
    record = SimpleNamespace(document_id="synthetic-doc", owner_user_id=OWNER, status="ready",
        index_state="indexed", document_kind="knowledge", document_version_id="synthetic-version",
        knowledge_collection_id="synthetic-collection", display_name="Synthetic")
    foreign = SimpleNamespace(**{**vars(record), "owner_user_id": "synthetic-other"})
    values = {"synthetic-doc": record, "synthetic-foreign": foreign, "synthetic-missing": None}
    matches = [RetrievedChunk(document_id=key, document_kind="knowledge", chunk_id=f"synthetic-chunk-{i}",
        chunk_index=i, content="Synthetic content", score=score)
        for i, (key, score) in enumerate([("synthetic-doc", .4), ("synthetic-doc", .9),
            ("synthetic-foreign", .99), ("synthetic-missing", .8)])]
    service = object.__new__(KnowledgeRetrievalService); service.settings = settings
    filter = RetrievalFilter(owner_user_id=OWNER, document_kinds=["knowledge"],
        document_version_ids=["synthetic-version"], knowledge_collection_ids=["synthetic-collection"])
    for batch in (True, False):
        repository = Mock(spec=["get_by_id", "get_by_ids"] if batch else ["get_by_id"])
        repository.get_by_id.side_effect = values.get
        if batch: repository.get_by_ids.side_effect = lambda ids: {key: values.get(key) for key in ids}
        service.document_repository = repository
        result = service._apply_metadata_filter(matches, filter=filter)
        require([item.score for item in result] == [.9, .4]
            and all(item.metadata["ownerUserId"] == OWNER for item in result), "metadata_owner_or_sort_changed")
        require(repository.get_by_id.call_count == (0 if batch else 3)
            and (not batch or repository.get_by_ids.call_args.args == (list(values),)),
            "metadata_unique_read_contract_changed")
    # Actual mode guards, including the service boundary, execute before any
    # real billing/ASR/provider method. Instances deliberately have no such deps.
    require_standard_session(SimpleNamespace(session_mode="interview"))
    require_standard_session(SimpleNamespace(session_mode="written"))
    for mode, code in (("mock", "mock_dedicated_command_required"), ("written", "written_exam_audio_disabled")):
        realtime = object.__new__(RealtimeSpeechService)
        realtime.settings = settings
        realtime._session_activity_lock = threading.Lock()
        realtime._session_cleanup_locks = {}; realtime._session_cleanup_lock_users = {}
        realtime.session_service = SimpleNamespace(get_session=lambda **_: SimpleNamespace(session_mode=mode))
        try:
            realtime.control_capture(user_id=OWNER, session_id=SESSION, action="pause")
        except DomainRequestError as error:
            require(error.status_code == 409 and error.error_code == code, "legacy_mode_error_changed")
        else:
            raise ProbeError("legacy_mode_guard_bypassed")
        require(realtime._session_cleanup_locks == realtime._session_cleanup_lock_users == {},
            "mode_guard_left_cleanup_lock")
    return {"metadataBatchAndFallbackPassed": True, "ordinaryWrittenMockGuardsPassed": True}


def synthetic_loop_monitor():
    from app.platform.cn_realtime_loop_monitor import CnMainLoopMonitor
    monitor = CnMainLoopMonitor(max_samples=3, emit_every=1000)
    for value in [1, 10, 50, 250, 500, float("nan"), float("inf"), -1]: monitor.observe(value)
    values = monitor.summary()
    require(values["sampleCount"] == values["capacity"] == 3 and values["observations"] == 5
        and values["maxMs"] == values["p95Ms"] == 500 and values["over250Ms"] == 2
        and all(type(value) in (int, float) and isfinite(value) and value >= 0 for value in values.values()),
        "loop_monitor_bounds_or_privacy_changed")
    return {"loopMonitorBoundedNumericPassed": True}



def synthetic_pinned_binding(settings):
    # Execute the actual repository/getter/service code with a scripted Redis
    # transport. Actual Lua execution and scale counts were tested separately
    # against an owned localhost Redis; no Redis is contacted by this probe.
    from dataclasses import asdict
    from app.services.cn_realtime_entity_state import CNRealtimeEntityState
    from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository
    from app.services import realtime_speech_service as realtime
    costs = []
    for history in (1, 1191, 10000):
        target = fixture(settings)
        target.state.binding = replace(target.state.binding, capabilities={"large": 2**53 + 1, "array": []})
        raw = json.dumps(asdict(target.state.binding))
        calls = []
        class SyntheticRedis:
            def hget(self, key, field):
                calls.append("hget")
                if key == "synthetic-codes" and field == CODE: return DEVICE
                if key == "synthetic-devices" and field == DEVICE: return json.dumps(asdict(target.state.device))
                raise ProbeError("unexpected_pinned_read")
            def hvals(self, key):
                raise ProbeError("pinned_global_scan_forbidden")
        store = object.__new__(CNRealtimeEntityState)
        store.redis = SyntheticRedis(); store._legacy_deadline = None; store.ttl = 300
        store.base = "synthetic-runtime"; store.keys = ["synthetic-key-" + str(i) for i in range(15)]
        def scripted(*, keys, args):
            calls.append("scripted_evalsha")
            require(args[0] == "pinned_binding_lookup" and args[4:] == [SESSION, target.state.binding.binding_id, DEVICE, CODE],
                    "pinned_identity_arguments_changed")
            return [raw, 0]
        store._script = scripted
        repository = object.__new__(RedisRealtimeSpeechRepository)
        repository._cn_controls = store; repository._redis = store.redis
        repository._device_code_index_key = "synthetic-codes"; repository._device_entity_key = "synthetic-devices"
        repository._runtime_lock = threading.RLock()
        repository.desktop_devices_by_id = {}; repository.desktop_devices_by_code = {}
        target.service.repository = repository
        target.service._capture_control_cache = {SESSION: "capturing"}
        with patch.object(realtime, "_now_ms", return_value=NOW):
            result = target.service._compute_desktop_pairing_status(manual_code=CODE, device_id=DEVICE,
                pinned_session_id=SESSION, pinned_binding_id=target.state.binding.binding_id)
        require(result["bound"] is True and result["bindingLockState"] == "held", "pinned_wire_contract_changed")
        require(result["binding"]["capabilities"] == target.state.binding.capabilities, "pinned_precision_changed")
        require(calls == ["hget", "hget", "scripted_evalsha"], "pinned_network_cost_changed")
        target.repository.get_control_state.assert_called_once_with(SESSION)
        target.repository.get_session.assert_not_called()
        costs.append(len(calls))
        retired_raw = store._script
        store._script = lambda **kw: [raw, 1]
        require(repository.get_pinned_session_desktop_binding(device_id=DEVICE, manual_code=CODE,
            session_id=SESSION, binding_id=target.state.binding.binding_id).status == "stale", "pinned_retirement_changed")
        store._script = lambda **kw: ["", -1]
        try:
            repository.get_pinned_session_desktop_binding(device_id=DEVICE, manual_code=CODE,
                session_id=SESSION, binding_id=target.state.binding.binding_id)
        except ValueError as error:
            require(str(error) == "cn_runtime_entity_identity_mismatch", "pinned_identity_error_changed")
        else:
            raise ProbeError("pinned_identity_error_swallowed")
    return {"pinnedSyntheticScaleCases": len(costs), "pinnedPairingTransportCalls": costs,
            "pinnedActualLuaExecutedInImageProbe": False, "pinnedGlobalScanForbidden": True,
            "pinnedIdentityRetirementPrecisionPassed": True}


async def synthetic_cleanup_control(settings, request):
    from collections import deque
    from dataclasses import asdict
    import time
    from app.ports.realtime_speech import AccountDesktopDeviceRecord
    from app.services.cn_realtime_entity_state import CNRealtimeEntityState
    from app.services.redis_realtime_speech_repository import RedisRealtimeSpeechRepository
    from app.services import realtime_speech_service as realtime
    from app.services.dashscope_realtime_asr_gateway import DashScopeRealtimeAsrGateway, _SourceRealtimeSession
    from app.services.cn_provider_close_executor import CnProviderCloseExecutor
    from app.services.cn_realtime_io_executor import CnRealtimeIoExecutor

    target = fixture(settings)
    binding = replace(target.state.binding, capabilities={"array": [], "precision": 2**53+1})
    account = AccountDesktopDeviceRecord(OWNER, DEVICE, CODE, 1, 2)
    store = object.__new__(CNRealtimeEntityState)
    store._legacy_deadline = None; store.ttl = 300; store.base = "synthetic-runtime"
    store.keys = ["synthetic-key-"+str(i) for i in range(18)]
    calls = []
    def scripted(*, keys, args):
        calls.append(args[0])
        require(args[4:] == [OWNER], "owner_reference_identity_changed")
        record = binding if args[0] == "owner_bindings" else account
        require(args[0] in {"owner_bindings", "owner_accounts"}, "owner_read_operation_changed")
        return [[json.dumps(asdict(record)), 0]]
    store._script = scripted
    repository = object.__new__(RedisRealtimeSpeechRepository)
    repository._cn_controls = store
    require(repository.list_session_desktop_bindings_for_user(user_id=OWNER) == [binding]
        and repository.list_account_desktop_devices(user_id=OWNER) == [account]
        and calls == ["owner_bindings", "owner_accounts"], "owner_read_dispatch_changed")
    # Lua execution and scale budgets are proved by the real local Redis suite;
    # this isolated image probe only verifies the shipped Python dispatch.
    service = object.__new__(realtime.RealtimeSpeechService)
    service.settings = settings
    service.logger = logging.getLogger("synthetic-lightweight-ack")
    service.logger.setLevel(logging.INFO)
    access = Mock()
    service.session_service = SimpleNamespace(get_control_state=access, get_session=deny)
    service._trace_lock = threading.Lock(); service._trace_records = {}; service._trace_order = deque(maxlen=4096)
    service._latest_timing = lambda **kwargs: None
    with patch.object(realtime, "log_event", side_effect=deny):
        for stage in ("transcript-delivery", "transcript-render", "answer-first-render", "screenshot-first-render"):
            event = service.acknowledge_runtime_timing(user_id=OWNER, session_id=SESSION,
                trace_id="synthetic-trace", stage=stage, duration_ms=20)
            require(event.kind == "performance-ack" and event.payload["stage"] == stage, "ack_wire_changed")
    require(access.call_count == 4, "ack_lightweight_authority_missing")

    gateway = DashScopeRealtimeAsrGateway(settings, logging.getLogger("synthetic-close"))
    entered, release = threading.Event(), threading.Event()
    def slow_close():
        entered.set(); require(release.wait(3), "synthetic_physical_close_not_released")
    old = _SourceRealtimeSession(SimpleNamespace(close=slow_close), 16000,
        time.monotonic(), time.monotonic(), SESSION+":microphone", "microphone")
    gateway._source_sessions[SESSION+":microphone"] = old
    try:
        require(gateway.close_source_deferred(session_id=SESSION, source_kind="microphone") == 1,
            "deferred_close_capability_missing")
        await until(entered.is_set, "deferred_close_not_started")
        require(old.closed and not old.accepting_transcript_events
            and SESSION+":microphone" not in gateway._source_sessions, "old_source_not_fenced")
        replacement = Mock()
        gateway._source_sessions[SESSION+":microphone"] = _SourceRealtimeSession(replacement, 16000,
            time.monotonic(), time.monotonic(), SESSION+":microphone", "microphone")
        release.set(); gateway.drain_deferred_closes()
        require(replacement.close.call_count == 0, "old_close_touched_replacement")
    finally:
        release.set(); gateway.close_all_sessions()

    # Both lifecycle workers are occupied; preparation must still progress.
    executor = CnRealtimeIoExecutor()
    ready, finish = [], threading.Event()
    def block():
        ready.append(1); require(finish.wait(3), "synthetic_lifecycle_not_released")
    blockers = [asyncio.create_task(executor.run(block, lane="lifecycle",
        operation_name="publisher_disconnect")) for _ in range(2)]
    create_entered, create_finish, cleaned = threading.Event(), threading.Event(), []
    def create():
        create_entered.set(); require(create_finish.wait(3), "synthetic_prepare_not_released"); return "synthetic-created"
    pending = None
    try:
        await until(lambda: len(ready) == 2, "both_lifecycle_workers_not_occupied")
        require(await asyncio.wait_for(executor.run(lambda: 23, lane="preparation",
            operation_name="publisher_prepare"), 1) == 23, "preparation_blocked_by_lifecycle")
        pending = asyncio.create_task(executor.run(create, lane="preparation",
            operation_name="publisher_create", on_abandoned_result=cleaned.append))
        await until(create_entered.is_set, "preparation_create_not_started")
        pending.cancel(); create_finish.set(); finish.set()
        result = await asyncio.gather(pending, return_exceptions=True)
        require(isinstance(result[0], asyncio.CancelledError) and cleaned == ["synthetic-created"],
            "preparation_cancel_cleanup_lost_or_replayed")
        await asyncio.gather(*blockers)
        diag = executor.diagnostics()["preparation"]
        require((diag["configuredWorkers"], diag["configuredQueueMax"]) == (2, 8), "preparation_capacity_changed")
    finally:
        finish.set(); create_finish.set()
        await asyncio.gather(*blockers, *([pending] if pending is not None else []), return_exceptions=True)
        executor.shutdown()

    # A submit can fail after enqueue. A late queued call must be a no-op.
    closer = CnProviderCloseExecutor(logging.getLogger("synthetic-submit"), workers=1, queue_max=0)
    queued, closed = [], []
    def failed_submit(operation, *args):
        queued.append((operation, args)); raise RuntimeError("synthetic-start-failure")
    try:
        with patch.object(closer._pool, "submit", failed_submit):
            closer.close(lambda: closed.append(1))
            operation, args = queued[0]; operation(*args)
            require(closed == [1] and closer.diagnostics()["pending"] == 0,
                "ambiguous_submit_replayed_close_or_permit")
    finally:
        closer.shutdown()
    return {"ownerScopedReadDispatchPassed": True, "ownerScopedReadActualLuaExecuted": False,
        "lightweightAckStages": 4, "disabledAckDebugSerializationSkipped": True,
        "detachedOldCloseCannotTouchReplacement": True, "preparationIndependentFromBothLifecycleWorkers": True,
        "preparationCancelledResourceCompensatedOnce": True, "ambiguousCloseSubmitExactlyOnce": True}


async def synthetic_mock_control_close():
    from app.modules import mock_interview as api
    from starlette.websockets import WebSocketDisconnect
    checked = 0
    for receiving in (WebSocketDisconnect, TimeoutError, ValueError, asyncio.CancelledError):
        for closing in (None, RuntimeError, WebSocketDisconnect):
            controller = SimpleNamespace(closed=False)
            events = []
            async def detach(value):
                require(value is controller, "mock_control_detach_owner_changed")
                events.append("detach")
                value.closed = True
            runtime = SimpleNamespace(attach=AsyncMock(return_value=controller),
                flush_draft=AsyncMock(), detach=AsyncMock(side_effect=detach))
            class Socket:
                reads = 0
                async def accept(self):
                    pass
                async def receive_text(self):
                    self.reads += 1
                    if self.reads == 1:
                        return json.dumps({"accessToken": "synthetic-token"})
                    await asyncio.sleep(0)
                    raise receiving()
                async def send_json(self, value):
                    raise ProbeError("unexpected_mock_control_send")
                async def close(self):
                    require(events == ["detach"] and controller.closed, "mock_control_close_before_detach")
                    events.append("close")
                    if closing:
                        raise closing()
            with patch.object(api, "require_mock_runtime", lambda: runtime), patch.object(api,
                    "authentication_service", lambda: SimpleNamespace(authenticate_access_token=lambda **_:
                        SimpleNamespace(user_id=OWNER))):
                cancelled = False
                try:
                    await api.mock_control(Socket(), SESSION)
                except asyncio.CancelledError:
                    cancelled = True
                require(cancelled == (receiving is asyncio.CancelledError), "mock_control_cancel_changed")
                require(events == ["detach", "close"] and runtime.detach.await_count == 1,
                    "mock_control_close_not_idempotent")
                checked += 1
    return {"mockControlCloseCases": checked, "mockControlExpectedDisconnectSafe": True,
        "mockControlCancellationPreserved": True}


async def scenarios(settings):
    from fastapi import Request
    from app.services import realtime_speech_service as realtime
    from app.services.realtime_control_executor import RealtimeControlExecutor
    asyncio.get_running_loop().set_default_executor(ThreadPoolExecutor(max_workers=1,
        thread_name_prefix="synthetic-cn-shared-probe"))
    executor = RealtimeControlExecutor(max_workers=1, queue_max=1)
    request = Request({"type": "http", "app": SimpleNamespace(state=SimpleNamespace(realtime_control_executor=executor))})
    try:
        with patch.object(realtime, "_now_ms", return_value=NOW):
            result = await synthetic_device_status(settings, request, executor)
            result["nonblockingExecutorCases"] = await synthetic_loop_responsiveness(settings, request, executor)
        result.update(await synthetic_voice_lanes(settings, request, executor))
        result.update(await synthetic_cancel_and_shutdown())
        result.update(synthetic_metadata_and_modes(settings))
        result.update(synthetic_loop_monitor())
        result.update(synthetic_pinned_binding(settings))
        result.update(await synthetic_cleanup_control(settings, request))
        result.update(await synthetic_mock_control_close())
        return result
    finally:
        executor.shutdown()


def main():
    require(isinstance(EXPECTED, dict), "release_expectations_missing")
    install_guards()
    root = Path("/app")
    actual, compiled = verify_source(root, EXPECTED)
    require(platform.python_version() == EXPECTED["python"] == "3.13.15", "python_version_changed")
    deps = dict(sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions()))
    require(deps == EXPECTED["dependencies"] and len(deps) == 44, "unapproved_dependency_change")
    sys.path.insert(0, str(root / "apps/backend"))
    from app.core.config import Settings
    settings = Settings(_env_file=None)
    require(settings.product_edition == "cn" and settings.environment == "production", "runtime_region_changed")
    values = settings.model_dump(mode="json")
    require(len(values) == 344 and sha(serialize(values)) == EXPECTED["settingsSha256"], "existing_settings_changed")
    require(settings.cn_hot_database_pool_enabled is False, "existing_pool_setting_changed")
    from app import main as application
    forbid_lifespan(application.app)
    schema = application.app.openapi()
    require(sha(json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()) == EXPECTED["openapiSha256"], "openapi_changed")
    require(len(schema["paths"]) == EXPECTED["httpPaths"] == 203, "api_routes_changed")
    # No ASGI lifespan, network, storage or real user data: verify listing
    # and old/new filename lookups against the candidate's frozen manifest.
    from app.modules import web as release_web
    published = release_web._published_desktop_manifest()
    visible = release_web._release_manifest()["entries"]
    require(len(visible) == 3 and all(e.get("version") == "2.0.0" for e in visible), "release_listing_invalid")
    require(len(published["entries"]) == 6 and all(release_web._published_desktop_entry(e["fileName"]) == e for e in published["entries"]), "release_history_invalid")
    from app.platform.cn_hot_database import cn_hot_database_diagnostics
    require(cn_hot_database_diagnostics(settings)["active"] is False, "pool_activated_unexpectedly")
    result = asyncio.run(scenarios(settings))
    for worker in WORKERS: worker.join(timeout=3)
    require(not any(worker.is_alive() for worker in WORKERS), "synthetic_worker_not_released")
    image = os.environ.get("OFFERSTEADY_RELEASE_PROBE_IMAGE", "")
    print(json.dumps({"passed": True, "image": image if re.fullmatch(r"sha256:[0-9a-f]{64}", image) else None,
        "runtimeFiles": len(actual), "compiledPython": compiled, "python": platform.python_version(),
        "dependencyCount": len(deps), "dependenciesUnchanged": True, "existingSettingsUnchanged": True,
        "settingsCount": len(values), "poolEnabled": False, "baselineAncillaryUnchanged": True,
        "companionReleaseManifestVerified": True, "companionVersion": "2.0.0",
        "settingsSha256": EXPECTED["settingsSha256"], "openapiSha256": EXPECTED["openapiSha256"], "httpPaths": len(schema["paths"]),
        "workerThreadsStarted": len(WORKERS), "allSyntheticWorkersReleased": True, "databaseOperations": 0,
        "networkRequests": 0, "fileWrites": 0, "lifespanEntered": False, "privateValuesPrinted": False, **result}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__,
            "errorCode": str(exc) if isinstance(exc, ProbeError) else "probe_failed", "privateValuesPrinted": False}))
        raise SystemExit(1) from None
