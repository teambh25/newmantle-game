import app.schemas as schemas


class V1Adapter:
    """
    Adapter for converting objects to V1 API format.
    """

    @staticmethod
    def answer_to_v1(answer):
        """
        Convert a new Answer object to V1 format.
        """
        return (
            schemas.Answer.model_validate_json(answer).word
            if answer is not None
            else None
        )
