CREATE TABLE IF NOT EXISTS user_quiz_results (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    quiz_date   DATE        NOT NULL,
    status      VARCHAR     NOT NULL DEFAULT 'FAIL',
    guess_count INTEGER     NOT NULL,
    hint_count  INTEGER     NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_user_quiz_date UNIQUE (user_id, quiz_date)
);

CREATE INDEX IF NOT EXISTS idx_user_quiz_results_user_id ON user_quiz_results(user_id);

CREATE TABLE IF NOT EXISTS outage_dates (
    date       DATE        PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
