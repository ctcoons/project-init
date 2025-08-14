from collections import defaultdict
from typing import Dict, List
from .project_data import FileReaderProjectData


class FileReaderResponse:
    def __init__(
            self,
            success: bool,
            message: str,
            project_data: FileReaderProjectData,
            independent_variables: Dict[str, List[str]] = None,
            data: Dict[str, Dict[str, Dict[str, str]]] = None,
            possible_typos: Dict[str, Dict[str, List[str]]] = None
    ):
        self.success = success
        self.message = message
        self.project_data = project_data

        # {Data_Tag: [Values]}
        self.independent_variables: Dict[str, List[str]] = independent_variables or defaultdict(list)

        # {Group: {Category: {Label: Value}}}
        self.data: Dict[str, Dict[str, Dict[str, str]]] = data or defaultdict(lambda: defaultdict(dict))

        # {Possible Typo: {Suggested Correction: [locations found]}}
        self.possible_typos: Dict[str, Dict[str, List[str]]] = possible_typos or defaultdict(lambda: defaultdict(list))

    def was_successful(self) -> bool:
        """Return whether the file reading process succeeded."""
        return self.success

    def get_message(self) -> str:
        return self.message

    def get_project_data(self) -> FileReaderProjectData:
        return self.project_data

    def get_data(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        return self.data

    def get_independent_variables(self) -> Dict[str, List[str]]:
        return self.independent_variables

    def get_possible_typos(self) -> Dict[str, Dict[str, List[str]]]:
        return self.possible_typos

    def __str__(self):
        return (
            f"FOR PROJECT={self.project_data.get_name()}\n"
            f"WITH GROUPS={self.project_data.get_groups()}\n"
            f"SUCCESS={self.success}\n"
            f"MESSAGE={self.message}\n"
            f"INDEPENDENT_VARS={dict(self.independent_variables)}\n"
            f"DATA={ {k: dict(v) for k, v in self.data.items()} }\n"
            f"POSSIBLE_TYPOS={ {k: dict(v) for k, v in self.possible_typos.items()} }"
        )
