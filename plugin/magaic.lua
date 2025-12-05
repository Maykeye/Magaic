local magaic = require("magaic") -- Load lua/magaic.lua

local function setup()
	vim.keymap.set("n", "<leader>mt", magaic.tee, { desc = "Pass the file through the model." })
	vim.keymap.set("v", "<leader>mr", magaic.llm_rewrite, { desc = "Rewrite the block" })

	local wk = require("which-key")
	if wk ~= nil then
		wk.add({
			{ "<leader>m", group = "[M]agaic", mode = { "n", "v" } },
			{ "<leader>m_", hidden = true },
		})
	end
end

setup()
