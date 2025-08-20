async def get_word_by_id(db: AsyncSession, word_id: str) -> str:
    word = await db.scalar(select(Vocabulary.word).where(Vocabulary.id == word_id))
    if word is None:
        raise EntityDoesNotExist(f'"word id {word_id}" not found')
    return word

async def insert_word_emb(db: AsyncSession, word: str, emb: np.array) -> Vocabulary:
    try:
        word_emb = Vocabulary(word=word, embedding=emb)
        db.add(word_emb)
        await db.commit()
        await db.refresh(word_emb)
    except IntegrityError:
        raise EntityAlreadyExists(f'"{word}" aleardy exists')
    return word_emb

async def calc_all_cosine_distance(db: AsyncSession, target_word: str) -> Tuple[list, float, float]:
    target_emb = select(Vocabulary.embedding).where(Vocabulary.word == target_word).scalar_subquery()
    q = select(
            Vocabulary.word,
            Vocabulary.embedding.cosine_distance(target_emb).label('dist')
        ).order_by('dist').offset(1) # except target
    res = await db.execute(q)
    return res.fetchall()