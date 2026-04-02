# Lua script for atomic guess recording.
# KEYS[1] = user:{user_id}:quiz:{date}:stat (Hash)
# ARGV[1] = result ('SUCCESS' or 'WRONG')
# ARGV[2] = TTL in seconds (set only on first access)
# Returns 1 if processed, 0 if skipped (terminal state)
RECORD_GUESS_SCRIPT = """
local status = redis.call('HGET', KEYS[1], 'status')
if status == 'SUCCESS' or status == 'GIVEUP' then
    return 0
end
redis.call('HINCRBY', KEYS[1], 'guesses', 1)
if ARGV[1] == 'SUCCESS' then
    redis.call('HSET', KEYS[1], 'status', 'SUCCESS')
    redis.call('EXPIRE', KEYS[1], ARGV[2])
elseif not status then
    redis.call('HSET', KEYS[1], 'status', 'FAIL')
    redis.call('EXPIRE', KEYS[1], ARGV[2])
end
return 1
"""

# Lua script for atomic hint recording.
# KEYS[1] = user:{user_id}:quiz:{date}:stat (Hash)
# ARGV[1] = TTL in seconds (set only on first access)
# Returns 1 if processed, 0 if skipped (terminal state)
RECORD_HINT_SCRIPT = """
local status = redis.call('HGET', KEYS[1], 'status')
if status == 'SUCCESS' or status == 'GIVEUP' then
    return 0
end
redis.call('HINCRBY', KEYS[1], 'hints', 1)
if not status then
    redis.call('HSET', KEYS[1], 'status', 'FAIL')
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return 1
"""

# Lua script for atomic give-up recording.
# KEYS[1] = user:{user_id}:quiz:{date}:stat (Hash)
# ARGV[1] = TTL in seconds (set only on first access)
# Returns 1 if processed, 0 if skipped (terminal state)
RECORD_GIVEUP_SCRIPT = """
local status = redis.call('HGET', KEYS[1], 'status')
if status == 'SUCCESS' or status == 'GIVEUP' then
    return 0
end
redis.call('HSET', KEYS[1], 'status', 'GIVEUP')
redis.call('EXPIRE', KEYS[1], ARGV[1])
return 1
"""

# Lua script for atomic guest-to-user stat key migration.
# KEYS[1] = guest key, KEYS[2] = user key
# Returns 0 if guest key absent (skip),
#         1 if user key already exists (guest key deleted),
#         2 if renamed successfully
LINK_GUEST_STAT_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    return 0
end
if redis.call('EXISTS', KEYS[2]) == 1 then
    redis.call('DEL', KEYS[1])
    return 1
end
redis.call('RENAME', KEYS[1], KEYS[2])
return 2
"""
