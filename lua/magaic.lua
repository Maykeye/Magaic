local M = {} -- Our module table

function M.tee()
	local path = vim.fn.expand("%:S") -- escape
	if path == nil then
		return error("No known filename")
	end

	local cmd = "!llama.cpp-raw-query.py --file " .. path
	return vim.cmd(cmd)
end

return M
