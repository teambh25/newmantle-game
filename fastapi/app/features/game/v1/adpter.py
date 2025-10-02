import app.schemas as schemas


class V1Adapter:
    @staticmethod
    def answer_to_v1(answer):
        return (
            schemas.Answer.model_validate_json(answer).word
            if answer is not None
            else None
        )
