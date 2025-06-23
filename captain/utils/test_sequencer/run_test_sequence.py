import asyncio
import logging
import subprocess
import time
import traceback
from typing import Callable, List, Union
import pydantic
from pathlib import Path
from captain.internal.manager import TSManager
from captain.models.test_sequencer import (
    IfNode,
    StatusTypes,
    TestNode,
    TestRootNode,
    TestSequenceElementNode,
    TestTypes,
)
from captain.parser.bool_parser.bool_parser import eval_expression
from captain.parser.bool_parser.expressions.models import Variable
from captain.types.test_sequence import MsgState, TestSequenceMessage
from captain.types.worker import PoisonPill
from captain.utils.config import ts_manager
from captain.utils.logger import logger
from captain.utils.time_utils import utcnow_str

# Cloud functionality removed
test_sequencer = None


def validate_test_path(path: str) -> str:
    """Validate and sanitize test file path to prevent security issues.

    Args:
        path: The file path to validate

    Returns:
        The validated absolute path

    Raises:
        ValueError: If the path is invalid or potentially dangerous
    """
    # Convert to Path object for better handling
    try:
        test_path = Path(path).resolve()
    except Exception as e:
        raise ValueError(f"Invalid path format: {e}")

    # Check if path exists
    if not test_path.exists():
        raise ValueError(f"Path does not exist: {test_path}")

    # Check if it's a file (not a directory)
    if not test_path.is_file():
        raise ValueError(f"Path is not a file: {test_path}")

    # Check for suspicious patterns
    path_str = str(test_path)
    if any(dangerous in path_str for dangerous in ["/etc/", "/root/", "/proc/", "/sys/"]):
        raise ValueError(f"Path contains potentially dangerous location: {test_path}")

    # Ensure the file has a valid extension for tests
    valid_extensions = {".py", ".robot"}
    if test_path.suffix not in valid_extensions:
        raise ValueError(f"Invalid file extension. Must be one of {valid_extensions}")

    return str(test_path)


class TestResult:
    def __init__(
        self,
        test_node: TestNode,
        result: bool,
        time_taken: float,
        error: str | None = None,
        created_at: str = utcnow_str(),
    ):
        self.test_node = test_node
        self.result = result
        self.time_taken = time_taken
        self.error = error
        self.created_at = created_at


class TestError:
    def __init__(self, error: str):
        self.error = error


class Context:
    def __init__(
        self,
        result_dict: dict[str, TestResult],
        identifiers: set[str],
    ):
        self.result_dict = result_dict
        self.identifiers = identifiers


Extract = tuple[
    Callable[[Context], Union[List[TestRootNode], List[TestSequenceElementNode], None]],
    Union[TestResult, None],
]


def _with_stream_test_result(func: Callable[[TestNode], Extract]):
    # TODO: support run in parallel feature
    async def wrapper(node: TestNode) -> Extract:
        await _stream_result_to_frontend(MsgState.running, test_id=node.id, result=StatusTypes.pending)
        test_sequencer._set_output_loc(node.id, rm_existing_data=True)
        logging.info(f"Running test {node.id} - min: {node.min_value} | max: {node.max_value}")
        test_sequencer._set_min_max(node.min_value, node.max_value)
        children_getter, test_result = func(node)
        measured_value = test_sequencer._get_most_recent_data(node.id)
        if test_result is None:
            raise Exception(f"{node.id}: Test returned None")
        else:
            await _stream_result_to_frontend(
                state=MsgState.test_done,
                test_id=node.id,
                result=StatusTypes.pass_ if test_result.result else StatusTypes.fail,
                time_taken=test_result.time_taken,  # TODO result, time_taken should be together
                created_at=test_result.created_at,
                error=test_result.error,
                value=float(measured_value) if isinstance(measured_value, float) or isinstance(measured_value, int) else None,
            )
        return children_getter, test_result

    return wrapper


@_with_stream_test_result
def _run_python(node: TestNode) -> Extract:
    """
    runs python file.
    @params file_path: path to the file
    @returns:
        bool: result of the test
        float: time taken to execute the test
        str: error message if any
    """
    start_time = time.time()
    try:
        # Validate the path before running
        validated_path = validate_test_path(node.path)
        logger.info(f"[Python Runner] Running {validated_path}")
        result = subprocess.run(["python", validated_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"[Python Runner] Running {result}")
        end_time = time.time()
        if result.returncode == 0:
            is_pass = True
        else:
            logger.info(f"TEST {validated_path} FAILED:\nSTDOUT: {result.stdout.decode()}\nSTDERR: {result.stderr.decode()}")
            is_pass = False
        return (
            lambda _: None,
            TestResult(
                node,
                is_pass,
                end_time - start_time,
                result.stderr.decode() if not is_pass else None,
                utcnow_str(),
            ),
        )
    except ValueError as e:
        end_time = time.time()
        logger.error(f"Path validation failed for {node.path}: {e}")
        return (
            lambda _: None,
            TestResult(
                node,
                False,
                end_time - start_time,
                f"Path validation error: {e}",
                utcnow_str(),
            ),
        )


@_with_stream_test_result
def _run_pytest(node: TestNode) -> Extract:
    """
    @params file_path: path to the file
    @returns:
        bool: result of the test
        float: time taken to execute the test
        str: error message if any
    """
    start_time = time.time()
    try:
        # Validate the path before running
        validated_path = validate_test_path(node.path)
        result = subprocess.run(["pytest", validated_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        end_time = time.time()

        if result.returncode == 0:
            is_pass = True
        else:
            logger.info(f"TEST {validated_path} FAILED:\nSTDOUT: {result.stdout.decode()}\nSTDERR: {result.stderr.decode()}")
            is_pass = False
        return (
            lambda _: None,
            TestResult(
                node,
                is_pass,
                end_time - start_time,
                result.stdout.decode() if not is_pass else None,
                utcnow_str(),
            ),
        )
    except ValueError as e:
        end_time = time.time()
        logger.error(f"Path validation failed for {node.path}: {e}")
        return (
            lambda _: None,
            TestResult(
                node,
                False,
                end_time - start_time,
                f"Path validation error: {e}",
                utcnow_str(),
            ),
        )


@_with_stream_test_result
def _run_placeholder(node: TestNode) -> Extract:
    """
    @params file_path: path to the file
    @returns:
        bool: result of the test
        float: time taken to execute the test
        str: error message if any
    """
    return (
        lambda _: None,
        TestResult(
            node,
            False,
            0,
            "Placeholder test not implemented",
            utcnow_str(),
        ),
    )


@_with_stream_test_result
def _run_robotframework(node: TestNode) -> Extract:
    """
    runs python file.
    @params file_path: path to the file
    @returns:
        bool: result of the test
        float: time taken to execute the test
        str: error message if any
    """
    start_time = time.time()
    try:
        # Validate the path before running
        validated_path = validate_test_path(node.path)
        logger.info(f"[Robot Framework Runner] Running {validated_path}")

        # Validate args if present
        if node.args is not None:
            # Filter out any potentially dangerous args
            safe_args = []
            for arg in node.args:
                # Skip args that could be dangerous
                if not any(danger in str(arg) for danger in ["..", ";", "|", "&", ">", "<", "`", "$"]):
                    safe_args.append(arg)
                else:
                    logger.warning(f"Skipping potentially dangerous argument: {arg}")
            cmd = ["robot", "--test", *safe_args, validated_path]
        else:
            cmd = ["robot", validated_path]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"[Robot Framework Runner] Running {result}")
        end_time = time.time()
        if result.returncode == 0:
            is_pass = True
        else:
            logger.info(f"TEST {validated_path} FAILED:\nSTDOUT: {result.stdout.decode()}\nSTDERR: {result.stderr.decode()}")
            is_pass = False
        return (
            lambda _: None,
            TestResult(
                node,
                is_pass,
                end_time - start_time,
                result.stderr.decode() if not is_pass else None,
                utcnow_str(),
            ),
        )
    except ValueError as e:
        end_time = time.time()
        logger.error(f"Path validation failed for {node.path}: {e}")
        return (
            lambda _: None,
            TestResult(
                node,
                False,
                end_time - start_time,
                f"Path validation error: {e}",
                utcnow_str(),
            ),
        )


def _eval_condition(result_dict: dict[str, TestResult], condition: str, identifiers: set[str]):
    """
    evaluates condition expression.
    returns true or false
    """

    # convert result_dict to symbol table
    symbol_table: dict[str, Variable] = {}
    for key, val in result_dict.items():
        symbol_table[key] = Variable(val.result, val.time_taken)

    try:
        res = eval_expression(
            condition,
            symbol_table,
            identifiers,
        )
    except Exception as e:
        logger.error(e)
        raise e
    return res


# TODO use TSSignaler class to abstract this funcitonality
async def _stream_result_to_frontend(
    state: MsgState,
    test_id: str = "",
    result: StatusTypes = StatusTypes.pending,
    time_taken: float = 0,
    created_at: str = utcnow_str(),
    error: str | None = None,
    value: float | None = None,
):
    asyncio.create_task(
        ts_manager.ws.broadcast(
            TestSequenceMessage(
                state.value,
                test_id,
                result.value,
                time_taken,
                created_at,
                error,
                value,
            )
        )
    )
    await asyncio.sleep(0)  # necessary for task yield
    await asyncio.sleep(0)  # still necessary for task yield


async def _case_root(node: TestRootNode) -> Extract:
    return lambda _: node.children, None


async def _case_if_node(node: IfNode) -> Extract:
    def get_next_children_from_context(context: Context):
        result_dict, identifiers = context.result_dict, context.identifiers
        expression_eval = _eval_condition(result_dict, node.condition, identifiers)
        if expression_eval:
            return node.main
        else:
            return node.else_

    return get_next_children_from_context, None


map_to_handler_run = (
    "type",
    {
        "root": (None, _case_root),
        "test": (
            "test_type",
            {
                TestTypes.python: (None, _run_python),
                TestTypes.pytest: (None, _run_pytest),
                TestTypes.placeholder: (None, _run_placeholder),
                TestTypes.robotframework: (None, _run_robotframework),
            },
        ),
        "conditional": (
            "conditional_type",
            {
                "if": (None, _case_if_node),
            },
        ),
    },
)


async def _extract_from_node(node: TestRootNode | TestSequenceElementNode, map_to_handler) -> Extract:
    if not bool(node.__dict__):
        return lambda _: None, None
    matcher, cur = map_to_handler
    while not callable(cur):
        matcher, cur = cur[node.__dict__[matcher]]
    children_getter, test_result = await cur(node)
    return children_getter, test_result


# TODO have pydantic model for data, convert camelCase to snake_case
async def run_test_sequence(data, ts_manager: TSManager):
    data = pydantic.TypeAdapter(TestRootNode).validate_python(data)
    identifiers = set(data.identifiers)
    context = Context({}, identifiers)
    try:

        async def run_dfs(node: TestRootNode | TestSequenceElementNode):
            if isinstance(node, TestNode):
                await ts_manager.wait_if_paused(node.id)

            children_getter, test_result = await _extract_from_node(node, map_to_handler_run)

            if test_result:
                context.result_dict[test_result.test_node.test_name] = test_result

            children = children_getter(context)
            if not children:
                return
            for child in children:
                await run_dfs(child)

        await _stream_result_to_frontend(state=MsgState.test_set_start)
        await run_dfs(data)  # run tests
        await _stream_result_to_frontend(state=MsgState.test_set_done)
    except PoisonPill as e:
        logger.info(f"PoisonPill received: {e}")
        # Broadcast handled in TSManager
    except Exception as e:
        await _stream_result_to_frontend(state=MsgState.error, error=str(e))
        logger.error(f"{e}: {traceback.format_exc()}")
