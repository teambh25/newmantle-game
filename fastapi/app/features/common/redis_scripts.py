# Lua script for atomic guess recording.
# KEYS[1] = user:{user_id}:quiz:{date}:stat (Hash)
# ARGV[1] = result ('SUCCESS' or 'WRONG')
# Returns 1 if processed, 0 if skipped (terminal state)
RECORD_GUESS_SCRIPT = """
local status = redis.call('HGET', KEYS[1], 'status')
if status == 'SUCCESS' or status == 'GIVEUP' then
    return 0
end
redis.call('HINCRBY', KEYS[1], 'guesses', 1)
if ARGV[1] == 'SUCCESS' then
    redis.call('HSET', KEYS[1], 'status', 'SUCCESS')
elseif not status then
    redis.call('HSET', KEYS[1], 'status', 'FAIL')
end
return 1
"""

# Lua script for atomic hint recording.
# KEYS[1] = user:{user_id}:quiz:{date}:stat (Hash)
# Returns 1 if processed, 0 if skipped (terminal state)
RECORD_HINT_SCRIPT = """
local status = redis.call('HGET', KEYS[1], 'status')
if status == 'SUCCESS' or status == 'GIVEUP' then
    return 0
end
redis.call('HINCRBY', KEYS[1], 'hints', 1)
if not status then
    redis.call('HSET', KEYS[1], 'status', 'FAIL')
end
return 1
"""

# Lua script for atomic give-up recording.
# KEYS[1] = user:{user_id}:quiz:{date}:stat (Hash)
# Returns 1 if processed, 0 if skipped (terminal state)
RECORD_GIVEUP_SCRIPT = """
local status = redis.call('HGET', KEYS[1], 'status')
if status == 'SUCCESS' or status == 'GIVEUP' then
    return 0
end
redis.call('HSET', KEYS[1], 'status', 'GIVEUP')
return 1
"""
