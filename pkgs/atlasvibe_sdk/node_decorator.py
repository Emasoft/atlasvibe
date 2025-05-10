# Copyright (c) 2024 Emasoft
#
# This software is licensed under the MIT License.
# Refer to the LICENSE file for more details.

import inspect
import os
import traceback
from contextlib import ContextDecorator
from functools import wraps
from inspect import signature
from typing import Any, Callable, Optional

from .config import logger 
from .connection_manager import DeviceConnectionManager 
from .data_container import DataContainer, Stateful
from .job_result_utils import get_dc_from_result, get_frontend_res_obj_from_result 
from .job_service import JobService 
from .models.JobResults.JobFailure import JobFailure 
from .models.JobResults.JobSuccess import JobSuccess 
from .node_init import NodeInitService 
from .parameter_types import format_param_value 
from .utils import get_hf_hub_cache_path 

__all__ = ["atlasvibe_node", "DefaultParams", "display"]


def fetch_inputs(previous_jobs: list[dict[str, str]]):
    """
    Queries for job results

    Parameters
    ----------
    previous_jobs : list of jobs that directly precede this node.
    Each item representing a job contains `job_id` and `input_name`.
    `input_name` is the port where the previous job with `job_id` connects to.

    Returns
    -------
    inputs : dict of DataContainer objects or list of DataContainer objects
    """
    dict_inputs: dict[str, DataContainer | list[DataContainer]] = dict()

    try:
        for prev_job in previous_jobs:
            prev_job_id = prev_job.get("job_id")
            input_name = prev_job.get("input_name", "")
            multiple = prev_job.get("multiple", False)
            edge = prev_job.get("edge", "") 

            logger.debug(
                f"fetching input from prev job id: {prev_job_id} "
                + f"for input port: {input_name} from output edge: {edge}"
            )

            job_result_dict = JobService().get_job_result(prev_job_id) 
            if not job_result_dict:
                raise ValueError(
                    f"Tried to get job result from {prev_job_id} but it was None"
                )

            actual_result_dc = None
            if isinstance(job_result_dict, DataContainer):
                if edge == "default" or not edge : 
                    actual_result_dc = job_result_dict
                else: 
                    logger.warning(f"Requested edge '{edge}' from a single DataContainer output of job {prev_job_id}. Using the DataContainer itself.")
                    actual_result_dc = job_result_dict 
            elif isinstance(job_result_dict, dict):
                target_output_key = edge if edge else "default" 
                if target_output_key in job_result_dict:
                    actual_result_dc = get_dc_from_result(job_result_dict[target_output_key])
                else: 
                    if "default" in job_result_dict:
                         actual_result_dc = get_dc_from_result(job_result_dict["default"])
                         logger.warning(f"Output edge '{target_output_key}' not found in job {prev_job_id}. Using 'default' output instead.")
                    else: 
                        if len(job_result_dict) == 1:
                            single_key = list(job_result_dict.keys())[0]
                            actual_result_dc = get_dc_from_result(job_result_dict[single_key])
                            logger.warning(f"Output edge '{target_output_key}' not found in job {prev_job_id}. Using the only available output '{single_key}'.")
                        else:
                            raise KeyError(f"Output edge '{target_output_key}' not found in job result dict from {prev_job_id} and no clear default available. Available keys: {list(job_result_dict.keys())}")
            else: 
                raise TypeError(f"Unexpected job result type from {prev_job_id}: {type(job_result_dict)}")


            if actual_result_dc is not None:
                logger.debug(f"got job result from {prev_job_id} for input '{input_name}'")
                if multiple:
                    if input_name not in dict_inputs:
                        dict_inputs[input_name] = [actual_result_dc]
                    elif isinstance(dict_inputs[input_name], list):
                        (dict_inputs[input_name] ).append(actual_result_dc)
                    else: 
                        logger.error(f"Input '{input_name}' was expected to be multiple but already set as single. Overwriting with list.")
                        dict_inputs[input_name] = [dict_inputs[input_name], actual_result_dc] # type: ignore
                else:
                    dict_inputs[input_name] = actual_result_dc
            else:
                logger.warning(f"Could not extract DataContainer for input '{input_name}' from job {prev_job_id} using edge '{edge}'.")


    except Exception as e:
        logger.error(f"Error fetching inputs: {e} {traceback.format_exc()}")
        
    return dict_inputs


class DefaultParams:
    def __init__(
        self, node_id: str, job_id: str, jobset_id: str, node_type: str
    ) -> None:
        self.node_id = node_id
        self.job_id = job_id
        self.jobset_id = jobset_id
        self.node_type = node_type


class cache_huggingface_to_atlasvibe(ContextDecorator): 
    """Context manager to override the HF_HOME env var"""

    def __enter__(self):
        self.old_env_var = os.environ.get("HF_HOME")
        os.environ["HF_HOME"] = get_hf_hub_cache_path()
        return self

    def __exit__(self, *exc):
        if self.old_env_var is None:
            if "HF_HOME" in os.environ: 
                 del os.environ["HF_HOME"]
        else:
            os.environ["HF_HOME"] = self.old_env_var
        return False


def display(
    original_function: Callable[..., DataContainer | dict[str, Any]] | None = None,
):
    if original_function is None:
        def decorator(func):
            return func
        return decorator
    return original_function


def atlasvibe_node( 
    original_function: Callable[..., Optional[DataContainer | dict[str, Any]]]
    | None = None,
    *,
    node_type: Optional[str] = None, 
    deps: Optional[list[str]] = None, 
    inject_node_metadata: bool = False,
    inject_connection: bool = False,
):
    """
    Decorator to turn Python functions with numerical return
    values into atlasvibe nodes.

    @atlasvibe_node is intended to eliminate boilerplate in connecting
    Python scripts as visual nodes

    Into whatever function it wraps, @atlasvibe_node injects
    1. the last node's input as list of DataContainer object
    2. parameters for that function (either set by the user or default)

    Parameters
    ----------
    `func`: Python function that returns DataContainer object or dict of DCs.

    Returns
    -------
    A dict containing DataContainer object(s) suitable for the backend.

    Usage Example
    -------------
    ```
    from atlasvibe_sdk import atlasvibe_node, DataContainer
    import numpy as np

    @atlasvibe_node
    def SINE(dc_inputs:list[DataContainer], params:dict[str, Any]): 

        dc_input = dc_inputs.get('default') 

        if dc_input:
            output = DataContainer(
                x=dc_input.x,
                y=np.sin(dc_input.x)
            )
            return output
        return None 
    ```
    """

    def decorator(func: Callable[..., Optional[DataContainer | dict[str, Any]]]):
        decorated_func = cache_huggingface_to_atlasvibe()(func)

        @wraps(decorated_func)
        def wrapper(
            node_id: str,
            job_id: str,
            jobset_id: str,
            observe_blocks: list[str], 
            previous_jobs: list[dict[str, str]] = [],
            ctrls: dict[str, Any] | None = None,
        ):
            try:
                logger.debug(f"Executing node: {func.__name__} (ID: {node_id})")
                logger.debug(f"Previous jobs: {previous_jobs}")
                
                func_params: dict[str, Any] = {}
                if ctrls is not None:
                    for ctrl_key, input_spec in ctrls.items(): 
                        param_name = input_spec.get("param")
                        param_value = input_spec.get("value")
                        param_type = input_spec.get("type")
                        if param_name: 
                            func_params[param_name] = format_param_value(param_value, param_type)
                        else:
                            logger.warning(f"Control '{ctrl_key}' for node {node_id} is missing 'param' name.")
                
                logger.debug(
                    f"Fetching inputs for node_id: {node_id} from previous_jobs: {previous_jobs}"
                )
                dict_inputs = fetch_inputs(previous_jobs)

                logger.debug(f"Constructing inputs for {func.__name__}")
                args_for_func: dict[str, Any] = {}
                
                sig = signature(decorated_func)

                for p_name, p_obj in sig.parameters.items():
                    if p_name in dict_inputs:
                        args_for_func[p_name] = dict_inputs[p_name]
                    elif p_name in func_params:
                        args_for_func[p_name] = func_params[p_name]
                    elif p_name == "default_params" and inject_node_metadata:
                        continue 
                    elif p_name == "init_container" and NodeInitService().has_init_store(node_id):
                        continue 
                    elif p_name == "connection" and inject_connection:
                        continue 
                    elif p_obj.default is not inspect.Parameter.empty:
                        pass 
                    elif p_name not in ['args', 'kwargs', '*args', '**kwargs']: 
                        logger.warning(f"Parameter '{p_name}' for function {func.__name__} not found in inputs or controls and has no default.")

                if inject_node_metadata:
                    if "default_params" in sig.parameters:
                        args_for_func["default_params"] = DefaultParams(
                            job_id=job_id,
                            node_id=node_id,
                            jobset_id=jobset_id,
                            node_type=node_type if node_type else func.__name__, # Use func name if node_type not provided
                        )
                    else: 
                        pass

                if NodeInitService().has_init_store(node_id):
                    if "init_container" in sig.parameters:
                         args_for_func["init_container"] = NodeInitService().get_init_store(node_id)

                if inject_connection:
                    if "connection" in sig.parameters:
                        device_param_name = func_params.get("connection") 
                        if not device_param_name and "connection" in dict_inputs: 
                            device_param_name = dict_inputs["connection"]

                        if not device_param_name: 
                            for p_key, p_val in func_params.items():
                                if "device" in p_key or "connection" in p_key: 
                                    if isinstance(p_val, (str, dict)): 
                                        device_param_name = p_val
                                        break
                        
                        if not device_param_name:
                             raise ValueError(
                                "Connection injection requested, but no device identifier found in parameters (e.g., a 'connection' parameter specifying the device ID)."
                            )
                        
                        _id = None
                        if isinstance(device_param_name, dict):
                            _id = device_param_name.get('id') or device_param_name.get('get_id') 
                        elif isinstance(device_param_name, str):
                            _id = device_param_name
                        
                        if not _id and hasattr(device_param_name, 'get_id'): 
                            _id = device_param_name.get_id()

                        if not _id:
                             raise ValueError(
                                f"Could not determine device ID from connection parameter: {device_param_name}"
                            )

                        connection_instance = DeviceConnectionManager.get_connection(_id)
                        if not connection_instance:
                            raise ConnectionError(f"Failed to get connection for device ID: {_id}")
                        args_for_func["connection"] = connection_instance
                    else:
                        logger.warning("'inject_connection' is True, but 'connection' not found in function signature.")

                if "default" not in args_for_func and "default" in sig.parameters:
                    unnamed_inputs = [v for k, v in dict_inputs.items() if k not in sig.parameters]
                    if len(unnamed_inputs) == 1:
                        args_for_func["default"] = unnamed_inputs[0]
                    else: 
                        if sig.parameters["default"].default is not inspect.Parameter.empty:
                            pass # Let it use its defined default
                        else:
                            logger.warning(f"Required 'default' parameter for {func.__name__} not provided.")


                logger.debug(f"Final arguments for {func.__name__}: {list(args_for_func.keys())}")

                dc_obj_or_dict = decorated_func(**args_for_func)
                
                if isinstance(dc_obj_or_dict, DataContainer) and not isinstance(
                    dc_obj_or_dict, Stateful 
                ):
                    dc_obj_or_dict.validate()
                elif isinstance(dc_obj_or_dict, dict):
                    for key, value in dc_obj_or_dict.items():
                        if isinstance(value, DataContainer) and not isinstance(value, Stateful):
                            value.validate()
                elif dc_obj_or_dict is None and sig.return_annotation is not None and sig.return_annotation != type(None):
                    pass

                JobService().post_job_result(job_id, dc_obj_or_dict)

                FN = func.__name__ 
                frontend_result_obj = get_frontend_res_obj_from_result(
                    node_id, observe_blocks, dc_obj_or_dict
                )
                return JobSuccess(
                    result=frontend_result_obj,
                    fn=FN,
                    node_id=node_id,
                    jobset_id=jobset_id,
                )

            except Exception as e:
                logger.error(f"Error in node {func.__name__} (ID: {node_id}): {str(e)}")
                logger.debug(traceback.format_exc())
                return JobFailure(
                    func_name=func.__name__, 
                    node_id=node_id,
                    error=str(e) + "\n" + traceback.format_exc(), 
                    jobset_id=jobset_id,
                )

        return wrapper

    if original_function:
        return decorator(original_function)

    return decorator
