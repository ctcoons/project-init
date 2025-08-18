from collections import defaultdict
from pyexpat.errors import messages

from core.models import ProjectData
from core.utils.subjects.subject_reader_response import SubjectReaderResponse


class SubjectReader:

    def __init__(self, csv: str, project_data: ProjectData):
        self.csv = csv
        self.project_data = project_data
        self.header = None


    def get_subject_reader_response(self) -> SubjectReaderResponse:
        resp = SubjectReaderResponse(
            success=True,
            message="Success",
            group_subject=defaultdict(str)
        )

        csv = None

        try:
            with open(self.csv, "r") as open_file:
                csv = open_file
                self.header = csv.readline()
        except Exception as e:
            resp.success = False
            resp.message = "Failed To Open File: " + str(e)
            return resp


        return resp





