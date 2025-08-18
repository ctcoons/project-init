

class SubjectReaderResponse:

    def __init__(self,
                 success: bool,
                 message: str,
                 group_subject: dict
                 ):

        self.success = success
        self.message = message
        self.group_subject = group_subject

    def was_successful(self):
        return self.success

    def get_message(self):
        return self.message

    def get_group_subject(self):
        return self.group_subject


