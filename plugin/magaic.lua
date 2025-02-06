
local magaic = require("magaic") -- Load lua/hello_world.lua

local function setup()
    magaic.init_model()
    vim.api.nvim_create_user_command("MagicQuickAsk", magaic.general_quick_ask, { nargs=0, desc="Quick ask" })
    vim.api.nvim_create_user_command("MagicComplete", magaic.general_completion, { nargs=0, desc="Complete magaic buffer" })
    vim.api.nvim_create_user_command("MagicChat", magaic.chat_completion, { nargs=0, desc="Complete expanding to buffer" })
    vim.api.nvim_create_user_command("MagicShow", magaic.display_buffer, { nargs=0, desc="Show magaic buffer" })
    vim.api.nvim_create_user_command("MagicChangeModel", magaic.change_model, { nargs=0, desc="Change the model" })
    vim.keymap.set("n", "<leader>ms", magaic.display_buffer, {desc = "Show magic buffer"})
    vim.keymap.set("n", "<leader>mc", magaic.chat_completion, {desc = "Chat"})
    vim.keymap.set("n", "<leader>mr", magaic.general_completion, {desc = "Raw completition"})
    vim.keymap.set("n", "<leader>mm", magaic.change_model, {desc = "Look/change model"})
    local wk = require("which-key");
    if wk ~= nil then
        wk.register {
            ["<leader>m"] = { name = "[M]agaic", _ = "which_key_ignore"}
        }
    end
end

-- TODO: use m.setup() ?
--
setup()
