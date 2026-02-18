from .core import ToolSpec
from .git import SPEC as GIT_SPEC
from .list_dir import SPEC as LIST_DIR_SPEC
from .read_file import SPEC as READ_FILE_SPEC


TOOL_SPECS: dict[str, ToolSpec] = {
    "read_file": READ_FILE_SPEC,
    "list_dir": LIST_DIR_SPEC,
    "git": GIT_SPEC,
}
