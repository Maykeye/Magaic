local M = {} -- Our module table
local data_file = vim.fn.expand("$HOME/.config/nvim/magaic.cfg")
M.MODEL = "olmo2:7b-1124-instruct-q4_K_M"
VIEW_HEIGHT = 15

LLAMA_CPP_SERVER_THINK = "__llama_cpp_server_think"
LLAMA_CPP_SERVER_NOTHINK = "__llama_cpp_server_nothink"

function M.init_model()
	M.MODEL = "olmo2:7b-1124-instruct-q4_K_M"
	local file = io.open(data_file, "r")
	if file then
		local model_id = file:read("*a")
		M.MODEL = model_id
		file:close()
	end
end

function M.save_model_id()
	local file = io.open(data_file, "w")
	if file then
		file:write(M.MODEL)
		file:close()
	end
end

M.KNOWN_EMBEDDING_MODELS = {
	["all-minilm"] = 1,
}

function M.change_model()
	local text = vim.fn.system("ollama list")
	local lines = M.split_line(text)
	local best_match = nil
	local req = vim.fn.input("Switch " .. M.MODEL .. " to: ")
	local candidates = { { "header" } }
	print("\n")

	-- Add llama.cpo
	table.insert(lines, 2, LLAMA_CPP_SERVER_THINK) -- 1st line is header, it will be ignored
	table.insert(lines, 3, LLAMA_CPP_SERVER_NOTHINK)

	-- Remove embedding movdels from the list
	local filtered_lines = {}
	for _, line in ipairs(lines) do
		local prefix = line:gmatch("[^:]+")()
		if not M.KNOWN_EMBEDDING_MODELS[prefix] then
			filtered_lines[#filtered_lines + 1] = line
		end
	end
	lines = filtered_lines

	-- Match against the rest
	for i, line in ipairs(lines) do
		local current = line:gmatch("[^ ]+")()
		if i ~= 1 and current ~= nil then
			candidates[#candidates + 1] = { current .. "\n" }
			if req ~= "" and line:match(req) then
				if best_match ~= nil then
					print("Too many models match " .. req .. ": " .. best_match .. ", " .. current)
					return
				end
				best_match = current
			end
		end
	end

	if best_match == nil or req == "" then
		if req ~= "" then
			candidates[1] = { "Unable to match against " .. req .. ":\n", "Error" }
			vim.api.nvim_echo(candidates, false, {})
		else
			candidates[1] = { "Models:\n" }
			vim.api.nvim_echo(candidates, false, {})
		end
		return
	end
	print("Matched request " .. req .. " to " .. best_match .. ". Switched.")
	M.MODEL = best_match
	vim.g.MAGICAIC_MODEL = M.MODEL
	M.save_model_id()
end

function M.do_send_llama_cpp(is_chat, prompt)
	local run = function(args)
		-- TODO:
		if true then
			return vim.fn.system(args)
		end
		M.job_id = vim.fn.jobstart(args, {
			stdout_buffered = false,
			stderr_buffered = false,
			on_stdout = function(_, data, _)
				if data then
					-- Append each line of output to the buffer
					local lines = vim.api.nvim_buf_get_lines(M.buffer_id, -1, -1, true)
					for _, line in ipairs(data) do
						if line ~= "" then
							table.insert(lines, line)
						end
					end
					vim.api.nvim_buf_set_lines(M.buffer_id, -1, -1, true, lines)
				end
			end,
		})
		return ""
	end

	if is_chat then
		if M.MODEL == LLAMA_CPP_SERVER_THINK then
			return run({ "llama.cpp-raw-query.py", prompt })
		else
			return run({ "llama.cpp-raw-query.py", "--no-think", prompt })
		end
	end
	return run({ "llama.cpp-raw-query.py", "--raw", "--no-think", prompt })
end

function M.tee()
	local path = vim.fn.expand("%:S") -- escape
	if path == nil then
		return error("No known filename")
	end

	if M.MODEL == LLAMA_CPP_SERVER_NOTHINK or M.MODEL == LLAMA_CPP_SERVER_THINK then
		local cmd = "!llama.cpp-raw-query.py --tee --file " .. path
		return vim.cmd(cmd)
	end

	local cmd = "!ollama-tee.py  --file " .. path .. " " .. M.MODEL
	vim.cmd(cmd)
end

function M.do_send_ollama(is_chat, prompt)
	local generation_mode = "raw"
	if is_chat then
		generation_mode = "chat"
	end
	return vim.fn.system({ "ollama-query.py", M.MODEL, generation_mode, prompt })
end

function M.do_send(is_chat, prompt)
	if M.MODEL == LLAMA_CPP_SERVER_NOTHINK or M.MODEL == LLAMA_CPP_SERVER_THINK then
		return M.do_send_llama_cpp(is_chat, prompt)
	end
	return M.do_send_ollama(is_chat, prompt)
end

function M.split_line(str)
	local lines = {}
	for s in string.gmatch(str .. "\n", "(.-)\n") do
		table.insert(lines, s)
	end
	return lines
end

function M.clear_buffer(buffer_id)
	vim.api.nvim_buf_set_lines(buffer_id, 0, -1, false, {})
end

function M.replace_buffer_content(buffer_id, new_content)
	if type(new_content) == "string" then
		new_content = M.split_line(new_content)
	end
	M.clear_buffer(buffer_id)
	vim.api.nvim_buf_set_text(buffer_id, 0, 0, 0, 0, new_content)
end

function M.rfind(haystack, needle)
	local r_start, r_end = string.find(string.reverse(haystack), string.reverse(needle))
	if r_start == nil then
		return nil
	end
	local len = string.len(haystack)
	local n_start, n_end = len - r_end + 1, len - r_start + 1
	return n_start
end

function M.general_quick_ask()
	local q = vim.fn.input("Contextless: ")
	if q == "" then
		print("(cancelled)")
		return
	end
	q = "<USER>" .. q .. "\n<AI>"
	local text = M.do_send(true, q)
	local buf = M.get_buffer()
	M.replace_buffer_content(buf, q .. "\n" .. text)
end

function M.impl_completion(is_chat)
	local buf = M.get_buffer()
	local content = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
	local prompt = ""
	for line_num, text in ipairs(content) do -- table.concat eats empty lines
		if line_num ~= 1 then
			prompt = prompt .. "\n"
		end
		prompt = prompt .. text
	end
	local text = M.do_send(is_chat, prompt)
	if is_chat then
		local ai_pos = M.rfind(string.upper("prompt"), "\n<AI>") or 0
		local usr_pos = M.rfind(string.upper("prompt"), "\n<USR>") or 0
		local user_pos = M.rfind(string.upper("prompt"), "\n<USR>") or 0
		if usr_pos > ai_pos or user_pos > ai_pos or ai_pos == 0 then
			text = "\n<AI>: " .. text
		end
	end

	M.replace_buffer_content(buf, prompt .. text)
end

function M.general_completion()
	return M.impl_completion(false)
end

function M.chat_completion()
	return M.impl_completion(true)
end

function M.show_buffer(buffer_id)
	local wins = vim.api.nvim_list_wins()
	-- CHECK IF IT EXISTS
	for _, win_id in ipairs(wins) do
		local win_buf = vim.api.nvim_win_get_buf(win_id)
		if win_buf == buffer_id then
			return
		end
	end

	-- SPLIT
	vim.cmd(tostring(VIEW_HEIGHT) .. "split")
	vim.cmd("buffer " .. tostring(buffer_id))
	vim.cmd("setf markdown")
end

function M.get_buffer()
	if M.buffer_id ~= nil and not vim.api.nvim_buf_is_valid(M.buffer_id) then
		M.buffer_id = nil
	end

	if M.buffer_id == nil then
		M.buffer_id = vim.api.nvim_create_buf(true, true)
		vim.api.nvim_buf_set_name(M.buffer_id, "Magaic")
	end

	M.show_buffer(M.buffer_id)

	return M.buffer_id
end

function M.display_buffer()
	M.get_buffer()
end

return M
