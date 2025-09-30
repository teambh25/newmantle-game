import datetime

import app.exceptions as exc
import app.features.admin.schemas as schemas
import app.utils as utils


class Validator:
    def __init__(self, today: datetime.date, max_rank: int):
        self.today = today
        self.max_rank = max_rank

    def validate_quiz(self, quiz: schemas.Quiz):
        """
        Validate the properties of a Quiz object according to business rules.
        """
        if quiz.date < self.today:
            raise exc.QuizValidationError("Quiz date cannot be before today")
        if not utils.is_hangul_string(quiz.answer):
            raise exc.QuizValidationError("Answer is not hangul")
        if quiz.answer in quiz.scores:
            raise exc.QuizValidationError("Answer is included in scores")
        if len(quiz.scores) < self.max_rank:
            raise exc.QuizValidationError("The length of scores is less than max rank")
        if not all(utils.is_hangul_string(word) for word in quiz.scores):
            raise exc.QuizValidationError("The scores includes non-hangul word")

    def validate_delete_date(self, date: datetime.date):
        if date == self.today:
            raise exc.DateNotAllowed("Can't delete today's quiz")

    def validate_deleted_cnt(self, deleted_cnt: int, key_num: int):
        """
        Validate that all redis keys are deleted
        """
        if deleted_cnt == 0:
            raise exc.QuizNotFound("Quiz data not found")
        elif deleted_cnt != key_num:
            raise exc.QuizInconsistentError(
                f"Inconsistent quiz data detected, only {deleted_cnt} keys were found and deleted"
            )
