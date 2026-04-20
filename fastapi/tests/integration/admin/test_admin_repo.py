"""Integration tests for AdminRepo against a real Redis instance."""

import datetime
import json

import pytest
import pytest_asyncio

from app.features.admin.repository import AdminRepo
from app.features.common.redis_keys import (
    ANSWER_INDICATOR,
    RedisQuizData,
    RedisQuizKeys,
)

TEST_DATE = datetime.date(2099, 1, 1)
TEST_ANSWER_WORD = "정답"
TEST_ANSWER_JSON = json.dumps(
    {"word": TEST_ANSWER_WORD, "tag": "테스트", "description": "테스트"}
)


def _make_quiz(words_with_scores: dict[str, float]) -> RedisQuizData:
    keys = RedisQuizKeys.from_date(TEST_DATE)
    sorted_scores = sorted(words_with_scores.items(), key=lambda x: x[1], reverse=True)

    scores_map = {
        word: RedisQuizData.serialize_score_and_rank(score, rank)
        for rank, (word, score) in enumerate(sorted_scores, start=1)
    }
    scores_map[TEST_ANSWER_WORD] = ANSWER_INDICATOR

    ranking_map = {
        rank: RedisQuizData.serialize_word_and_score(word, score)
        for rank, (word, score) in enumerate(sorted_scores, start=1)
    }

    return RedisQuizData(
        keys=keys,
        answer=TEST_ANSWER_JSON,
        scores_map=scores_map,
        ranking_map=ranking_map,
        expire_at=RedisQuizKeys.get_expiry(TEST_DATE),
    )


@pytest_asyncio.fixture
async def admin_repo(redis_client):
    return AdminRepo(rd=redis_client)


@pytest_asyncio.fixture(autouse=True)
async def cleanup(redis_client):
    keys = RedisQuizKeys.from_date(TEST_DATE)
    await redis_client.delete(keys.answers_key, keys.scores_key, keys.ranking_key)
    await redis_client.srem("quiz:index", keys.answers_key)
    yield
    await redis_client.delete(keys.answers_key, keys.scores_key, keys.ranking_key)
    await redis_client.srem("quiz:index", keys.answers_key)


class TestUpsert:
    @pytest.mark.asyncio
    async def test_shrunk_upsert_drops_removed_words(self, admin_repo, redis_client):
        """Second upsert with fewer words must not leave removed words in scores/ranking."""
        keys = RedisQuizKeys.from_date(TEST_DATE)

        await admin_repo.upsert_quiz(
            _make_quiz(
                {"가나": 0.9, "나다": 0.8, "다라": 0.7, "라마": 0.6, "마바": 0.5}
            )
        )
        await admin_repo.upsert_quiz(
            _make_quiz({"가나": 0.9, "나다": 0.8, "다라": 0.7})  # drop "라마", "마바"
        )

        scores = await redis_client.hgetall(keys.scores_key)
        ranking_words = {
            v.split("|")[0]
            for v in (await redis_client.hgetall(keys.ranking_key)).values()
        }

        assert "라마" not in scores
        assert "마바" not in scores
        assert "가나" in scores

        assert "라마" not in ranking_words
        assert "마바" not in ranking_words
        assert "가나" in ranking_words

    @pytest.mark.asyncio
    async def test_expanded_upsert_adds_new_words(self, admin_repo, redis_client):
        """Second upsert with more words must include all new words in scores/ranking."""
        keys = RedisQuizKeys.from_date(TEST_DATE)

        await admin_repo.upsert_quiz(
            _make_quiz({"가나": 0.9, "나다": 0.8, "다라": 0.7})
        )
        await admin_repo.upsert_quiz(
            _make_quiz(
                {"가나": 0.9, "나다": 0.8, "다라": 0.7, "라마": 0.6, "마바": 0.5}
            )
        )

        scores = await redis_client.hgetall(keys.scores_key)
        ranking_words = {
            v.split("|")[0]
            for v in (await redis_client.hgetall(keys.ranking_key)).values()
        }

        assert "라마" in scores
        assert "마바" in scores
        assert "가나" in scores

        assert "라마" in ranking_words
        assert "마바" in ranking_words
        assert "가나" in ranking_words


class TestFetchAllAnswers:
    @pytest.mark.asyncio
    async def test_stale_keys_removed_from_index(self, admin_repo, redis_client):
        """fetch_all_answers must srem keys whose data has expired, return only live answers."""
        stale_key = "quiz:1999-01-01:answers"
        await redis_client.sadd("quiz:index", stale_key)

        keys = RedisQuizKeys.from_date(TEST_DATE)
        await admin_repo.upsert_quiz(_make_quiz({"가나": 0.9}))

        live_keys, live_answers = await admin_repo.fetch_all_answers()

        assert stale_key not in live_keys
        assert keys.answers_key in live_keys
        assert await redis_client.sismember("quiz:index", stale_key) == 0

        await redis_client.srem("quiz:index", stale_key)
