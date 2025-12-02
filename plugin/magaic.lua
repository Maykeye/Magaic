local magaic = require("magaic") -- Load lua/magaic.lua

local function setup()
	vim.keymap.set(
		"n",
		"<leader>mt",
		magaic.tee,
		{ desc = "Pass the file through the model. SAVE THE FILE BEFOREHAND" }
	)

	local wk = require("which-key")
	if wk ~= nil then
		wk.add({
			{ "<leader>m", group = "[M]agaic" },
			{ "<leader>m_", hidden = true },
		})
	end
end

setup()
