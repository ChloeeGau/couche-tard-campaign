# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Deployment script."""

import os
import sys
import json
import copy
import traceback

import vertexai
from absl import app, flags
from dotenv import load_dotenv

load_dotenv()

from google.adk.artifacts import GcsArtifactService
from google.api_core import exceptions as google_exceptions
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

from fashion.adk_common.utils import utils_gcs

PROD_AGENT_WHL_FILEPATH = "dist/davos_fashion_campaign-0.1.1-py3-none-any.whl"
STAGING_AGENT_WHL_FILEPATH = "dist/davos_fashion_campaign-0.1.1-py3-none-any.whl"

USED_AGENT_WHL_FILEPATH = STAGING_AGENT_WHL_FILEPATH

FLAGS = flags.FLAGS
flags.DEFINE_string("update_agent", None, "Agent Id to Update")

_env_vars = {}


def _get_env_vars() -> dict[str, str]:
    if not _env_vars:
        load_dotenv()
        env_var_keys = [
            "GOOGLE_CLOUD_PROJECT",
            "GOOGLE_CLOUD_LOCATION",
            "MODELS_CLOUD_LOCATION",
            "GOOGLE_CLOUD_BUCKET_AGENTDEPLOYMENT",
            "GOOGLE_CLOUD_BUCKET_ARTIFACTS",
            "DEMO_AGENT_DISPLAY_NAME",
            "DEMO_COMPANY_NAME",
            "LLM_GEMINI_MODEL_ROOT",
            "IMAGE_EDITION_MODEL",
            "MAX_NUMBER_OF_IMAGES",
            "GOOGLE_GENAI_USE_VERTEXAI",
            "AGENT_VERSION",
            "BACKUP_CATALOG_IMAGE_URL",
            "BACKUP_GENERATED_IMAGE_URL",
            "BACKUP_GENERATED_IMAGE_URL_LAKE",
            "BACKUP_GENERATED_IMAGE_URL_HELMET",
            "BACKUP_GENERATED_IMAGE_URL_SUNSET",
            "BACKUP_GENERATED_IMAGE_URL_FROZEN",
            "BACKUP_GENERATED_IMAGE_URL_FAST",
            "IS_DEBUG_ON",
        ]

        for key in env_var_keys:
            if value := os.environ.get(key):
                _env_vars[key] = value

        print(f"env vars: {json.dumps(_env_vars)}")

    return _env_vars


def get_artifact_service():
    import traceback

    try:
        artifactService = GcsArtifactService(
            bucket_name=_get_env_vars()["GOOGLE_CLOUD_BUCKET_ARTIFACTS"]
        )
        print(
            f"Artifact Service of Type: {type(artifactService)}. Created For Bucket: {artifactService.bucket_name}"
        )
        print(f"Current Stack: {traceback.extract_stack()}")
        return artifactService
    except Exception as e:
        print(f"ERROR. Failed to return GcsArtifactService with error: {e}")
        raise


def _create() -> None:
    # Import here so that it does not try to initialize config before load_dotenv called
    # from fashion.agent import root_agent
    from fashion.agent import root_agent
    # from app import agent

    deep_copy_env_vars = copy.deepcopy(_get_env_vars())

    """Creates and deploys the agent."""
    adk_app = AdkApp(
        agent=root_agent,
        enable_tracing=False,
        artifact_service_builder=get_artifact_service,
        env_vars=deep_copy_env_vars,
    )

    adk_app.set_up()
    print(f"get_artifact_service: {get_artifact_service}")
    print(f"artifact_service_builder: {adk_app._tmpl_attrs.get('artifact_service_builder')}")
    print(f"artifact_service: {adk_app._tmpl_attrs.get('artifact_service')}")
    # print(
    #     f"AdkApp has Artifact Service Builder: {adk_app._tmpl_attrs.get("artifact_service_builder")} - and Artifact Service: {adk_app._tmpl_attrs.get("artifact_service")}"
    # )

    if not os.path.exists(USED_AGENT_WHL_FILEPATH):
        print(
            "Agent wheel file not found at: %s - run `poetry build`",
            USED_AGENT_WHL_FILEPATH,
        )
        raise FileNotFoundError(
            f"Agent wheel file not found: {USED_AGENT_WHL_FILEPATH}"
        )

    deep_copy_env_vars.pop("GOOGLE_CLOUD_PROJECT")
    deep_copy_env_vars.pop("GOOGLE_CLOUD_LOCATION")
    deep_copy_env_vars.pop("GOOGLE_GENAI_USE_VERTEXAI")

    print("\nAttempting to create agent")

    remote_agent = agent_engines.create(
        adk_app,
        requirements=[USED_AGENT_WHL_FILEPATH],
        extra_packages=[USED_AGENT_WHL_FILEPATH],
        env_vars=deep_copy_env_vars,
        display_name=deep_copy_env_vars["DEMO_AGENT_DISPLAY_NAME"],
        description=f"{root_agent.description} [Version: {_env_vars['AGENT_VERSION']}].",
    )
    print(
        f"\nSuccessfully created agent: {remote_agent.resource_name}. Version: {deep_copy_env_vars['AGENT_VERSION']}"
    )


def _update(agent_to_update) -> None:
    # Import here so that it does not try to initialize config before load_dotenv called
    from root_agent.agent import root_agent

    deep_copy_env_vars = copy.deepcopy(_get_env_vars())

    """Creates and deploys the agent."""
    adk_app = AdkApp(
        agent=root_agent,
        enable_tracing=False,
        artifact_service_builder=get_artifact_service,
        env_vars=deep_copy_env_vars,
    )

    adk_app.set_up()

    print(
        f"AdkApp has Artifact Service Builder: {adk_app._tmpl_attrs.get('artifact_service_builder')} - and Artifact Service: {adk_app._tmpl_attrs.get('artifact_service')}"
    )

    if not os.path.exists(USED_AGENT_WHL_FILEPATH):
        print(
            "Agent wheel file not found at: %s - run `poetry build`",
            USED_AGENT_WHL_FILEPATH,
        )
        raise FileNotFoundError(
            f"Agent wheel file not found: {USED_AGENT_WHL_FILEPATH}"
        )

    deep_copy_env_vars.pop("GOOGLE_CLOUD_PROJECT")
    deep_copy_env_vars.pop("GOOGLE_CLOUD_LOCATION")
    deep_copy_env_vars.pop("GOOGLE_GENAI_USE_VERTEXAI")

    if not agent_to_update:
        print(f"Failed to update Agent, specify agent to update")
        raise RuntimeError("Failed to update Agent, no agent specified")

    print(f"\nAttempting to update agent: {agent_to_update}")

    existing_agent = agent_engines.AgentEngine(agent_to_update)
    if not existing_agent:
        print(f"No agent returned with Id: {agent_to_update}")
        raise RuntimeError(f"No agent returned with Id: {agent_to_update}")

    remote_agent = existing_agent.update(
        agent_engine=adk_app,
        requirements=[USED_AGENT_WHL_FILEPATH],
        extra_packages=[USED_AGENT_WHL_FILEPATH],
        env_vars=deep_copy_env_vars,
        display_name=deep_copy_env_vars["DEMO_AGENT_DISPLAY_NAME"],
        description=f"{root_agent.description} [Regulatory Version: {_env_vars['AGENT_VERSION']}].",
    )
    print(f"\nSuccessfully updated agent: {remote_agent.resource_name}")

# def main(argv: list[str]) -> None:  # pylint: disable=unused-argument
#     from app.agent import root_agent
#     print(_get_env_vars()["GOOGLE_CLOUD_PROJECT"])
#     print(_get_env_vars()["GOOGLE_CLOUD_LOCATION"])
#     print(_get_env_vars()["GOOGLE_CLOUD_BUCKET_AGENTDEPLOYMENT"])
#     deep_copy_env_vars = copy.deepcopy(_get_env_vars())
#     print(deep_copy_env_vars)
def main(argv: list[str]) -> None:  # pylint: disable=unused-argument
    # try:
    vertexai.init(
        project=_get_env_vars()["GOOGLE_CLOUD_PROJECT"],
        location=_get_env_vars()["GOOGLE_CLOUD_LOCATION"],
        staging_bucket=f"{utils_gcs.get_gcs_uri_from_bucket_name(_get_env_vars()['GOOGLE_CLOUD_BUCKET_AGENTDEPLOYMENT'])}",
    )

    agent_to_update = None
    should_update_agent = False
    if FLAGS.update_agent:
        agent_to_update = FLAGS.update_agent
        should_update_agent = True

    if should_update_agent:
        _update(agent_to_update)
    else:
        _create()

    # except google_exceptions.Forbidden as e:
    #     print(
    #         "\nPermission Error: Ensure the service account/user has necessary "
    #         "permissions (e.g., Storage Admin, Vertex AI User, Service Account User on runtime SA)."
    #         f"\nDetails: {e}",
    #         file=sys.stderr,
    #     )
    #     raise e
    # except google_exceptions.NotFound as e:
    #     print(f"\nResource Not Found Error: {e}", file=sys.stderr)
    #     raise e
    # except google_exceptions.GoogleAPICallError as e:
    #     print(f"\nGoogle API Call Error: {e}", file=sys.stderr)
    #     raise e
    # except FileNotFoundError as e:
    #     print(f"\nFile Error: {e}", file=sys.stderr)
    #     print(
    #         "Please ensure the agent wheel file exists and you have run the build script.",
    #         file=sys.stderr,
    #     )
    #     raise e
    # except Exception as e:
    #     print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
    #     raise e


if __name__ == "__main__":
    app.run(main)
