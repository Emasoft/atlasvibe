import { captain } from "./ky";
import { HTTPError } from "ky";
import {
  blockManifestSchema,
  blockMetadataSchema,
} from "@/renderer/types/manifest";
import { tryParse } from "@/types/result";
import { ZodError, z } from "zod";
import { EnvVar } from "@/renderer/types/env-var";
import { BlockData } from "@/renderer/types/block";
import { Edge, Node } from "reactflow";
import { BackendSettings } from "@/renderer/stores/settings";
import _ from "lodash";
import { ResultAsync, fromPromise } from "neverthrow";
import { Options } from "ky";
import { DeviceInfo } from "@/renderer/types/hardware";
import {
  TestDiscoverContainer,
  TestSequenceContainer,
} from "@/renderer/types/test-sequencer";
import { useProjectStore } from "@/renderer/stores/project";

const get = <Z extends z.ZodTypeAny>(
  url: string,
  schema: Z,
  options?: Options,
): ResultAsync<z.infer<Z>, HTTPError | ZodError> => {
  return fromPromise(
    captain.get(url, options).json(),
    (e) => e as HTTPError,
  ).andThen(tryParse(schema));
};

export const getManifest = (blocksPath?: string, projectPath?: string) => {
  const searchParams: any = {};
  if (blocksPath) searchParams.blocks_path = blocksPath;
  if (projectPath) searchParams.project_path = projectPath;

  return get("blocks/manifest", blockManifestSchema, { 
    searchParams: Object.keys(searchParams).length > 0 ? searchParams : undefined 
  });
};

export const saveBlueprintFromBlock = (params: {
  blockPath: string;
  blueprintName: string;
  overwrite?: boolean;
}) => {
  return fromPromise(
    captain.post("blocks/save-as-blueprint", {
      json: {
        block_path: params.blockPath,
        blueprint_name: params.blueprintName,
        overwrite: params.overwrite || false,
      },
    }).json(),
    (e) => e as HTTPError,
  );
};

export const renameBlueprint = (params: {
  oldName: string;
  newName: string;
}) => {
  return fromPromise(
    captain.put("blocks/rename-blueprint", {
      json: {
        old_name: params.oldName,
        new_name: params.newName,
      },
    }).json(),
    (e) => e as HTTPError,
  );
};

export const deleteBlueprint = (params: {
  blueprintName: string;
}) => {
  return fromPromise(
    captain.delete(`blocks/blueprint/${params.blueprintName}`).json(),
    (e) => e as HTTPError,
  );
};

export const getMetadata = (
  blocksPath?: string,
  customDirChanged: boolean = false,
  projectPath?: string,
) => {
  const searchParams: any = {};
  if (blocksPath) searchParams.blocks_path = blocksPath;
  if (projectPath) searchParams.project_path = projectPath;
  searchParams.custom_dir_changed = customDirChanged;

  return get("blocks/metadata", blockMetadataSchema, { searchParams });
};

export const getEnvironmentVariables = async () => get("env", EnvVar.array());

export const getEnvironmentVariable = async (key: string) =>
  get(`env/${key}`, EnvVar);

export const postEnvironmentVariable = async (body: EnvVar) => {
  return fromPromise(
    captain.post("env", { json: body }),
    (e) => e as HTTPError,
  );
};

export const deleteEnvironmentVariable = async (key: string) => {
  return fromPromise(captain.delete(`env/${key}`), (e) => e as HTTPError);
};

type RunFlowchartArgs = {
  nodes: Node<BlockData>[];
  edges: Edge[];
  observeBlocks: string[];
  jobId: string;
  settings: BackendSettings;
};

export const runFlowchart = async ({
  nodes,
  edges,
  observeBlocks,
  settings,
  jobId,
}: RunFlowchartArgs) => {
  // Get current project path from project store
  const projectPath = useProjectStore.getState().path;
  
  return fromPromise(
    captain.post("wfc", {
      json: {
        fc: JSON.stringify({ nodes, edges }),
        jobsetId: jobId,
        cancelExistingJobs: true,
        observeBlocks: observeBlocks,
        projectPath: projectPath,
        //IMPORTANT: if you want to add more backend settings, modify PostWFC pydantic model in backend, otherwise you will get 422 error
        ..._.mapValues(settings, (s) => s.value),
      },
    }),
    (e) => e as HTTPError,
  );
};

export async function cancelFlowchartRun(jobId: string) {
  return fromPromise(
    captain.post("cancel_fc", {
      json: {
        jobsetId: jobId,
      },
    }),
    (e) => e as HTTPError,
  );
}

export async function getDeviceInfo(
  discoverNIDAQmxDevices = false,
  discoverNIDMMDevices = false,
) {
  return get("devices", DeviceInfo, {
    searchParams: {
      include_nidaqmx_drivers: discoverNIDAQmxDevices,
      include_nidmm_drivers: discoverNIDMMDevices,
    },
  });
}

const LogLevel = z.object({
  level: z.string(),
});

export const getLogLevel = async () => {
  return get("log_level", LogLevel).map((v) => v.level);
};

export const setLogLevel = async (level: string) => {
  return fromPromise(
    captain.post("log_level", { json: { level } }),
    (e) => e as HTTPError,
  );
};

export const discoverPytest = async (path: string, oneFile: boolean) => {
  return get("discover/pytest", TestDiscoverContainer, {
    searchParams: {
      path,
      oneFile,
    },
  });
};

export const createCustomBlock = async (
  blueprintKey: string,
  newBlockName: string,
  projectPath: string,
) => {
  return fromPromise(
    captain.post("blocks/create-custom", {
      json: {
        blueprint_key: blueprintKey,
        new_block_name: newBlockName,
        project_path: projectPath,
      },
    }).json(),
    (e) => e as HTTPError,
  );
};

export const updateBlockCode = async (
  blockPath: string,
  content: string,
  projectPath: string,
) => {
  return fromPromise(
    captain.post("blocks/update-code", {
      json: {
        block_path: blockPath,
        content: content,
        project_path: projectPath,
      },
    }).json(),
    (e) => e as HTTPError,
  );
};

export const discoverRobot = async (path: string, oneFile: boolean) => {
  return get("discover/robot", TestDiscoverContainer, {
    searchParams: {
      path,
      oneFile,
    },
  });
};


const TestProfile = z.object({
  profile_root: z.string(),
  hash: z.string(),
});
export type TestProfile = z.infer<typeof TestProfile>;

export const installTestProfile = (url: string) => {
  const options: Options = { headers: { url: url }, timeout: 60000 };
  return get("test_profile/install", TestProfile, options);
};
