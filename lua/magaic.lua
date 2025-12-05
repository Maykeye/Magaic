local M = {} -- Our module table

function M.stream_cmd(cmd)
	vim.cmd("split")
	local buf = vim.api.nvim_create_buf(true, false)
	vim.api.nvim_set_current_buf(buf)

	vim.bo[buf].buftype = "nofile"
	vim.bo[buf].swapfile = false
	vim.bo[buf].bufhidden = "wipe"

	vim.fn.jobstart(cmd, {
		stdout_buffered = false,

		on_stdout = function(_, data, _)
			if data then
				local last_line_index = vim.api.nvim_buf_line_count(buf) - 1
				local last_line_content =
					vim.api.nvim_buf_get_lines(buf, last_line_index, last_line_index + 1, false)[1]

				data[1] = last_line_content .. data[1]

				vim.api.nvim_buf_set_lines(buf, last_line_index, last_line_index + 1, false, data)

				local new_last_line = vim.api.nvim_buf_line_count(buf)
				vim.api.nvim_win_set_cursor(0, { new_last_line, 0 })
			end
		end,

		on_stderr = function(_, data, _)
			if data then
				local last_line_index = vim.api.nvim_buf_line_count(buf) - 1
				local last_line_content =
					vim.api.nvim_buf_get_lines(buf, last_line_index, last_line_index + 1, false)[1]

				data[1] = last_line_content .. data[1]

				vim.api.nvim_buf_set_lines(buf, last_line_index, last_line_index + 1, false, data)

				local new_last_line = vim.api.nvim_buf_line_count(buf)
				vim.api.nvim_win_set_cursor(0, { new_last_line, 0 })
			end
		end,
	})
end

function M.tee()
	local path = vim.fn.expand("%:S") -- escape
	if path == nil then
		return error("No known filename")
	end

	local cmd = "!llama.cpp-raw-query.py --file " .. path
	return vim.cmd(cmd)
end

function M.llm_rewrite_impl(start_line, end_line, prompt)
	local file_path = vim.api.nvim_buf_get_name(0)

	vim.cmd("write")

	local cmd = {
		"llama.cpp-rewrite-with-chat.py",
		"--file",
		file_path,
		"--range",
		string.format("%d..%d", start_line, end_line),
		"--prompt",
		prompt,
	}

	M.stream_cmd(cmd)
end

function M.llm_rewrite()
	vim.ui.input({ prompt = "Rerwite: " }, function(prompt)
		if not prompt or prompt == "" then
			return
		end
		local start_line = vim.fn.line("'<")
		local end_line = vim.fn.line("'>") + 1
		M.llm_rewrite_impl(start_line, end_line, prompt)
	end)
end

return M
