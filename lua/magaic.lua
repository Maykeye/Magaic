local M = {}  -- Our module table


local data_file = vim.fn.expand("$HOME/.config/nvim/magaic.cfg")


M.MODEL="olmo2:7b-1124-instruct-q4_K_M"
VIEW_HEIGHT=15

function M.init_model()
  M.MODEL="olmo2:7b-1124-instruct-q4_K_M"
  local file = io.open(data_file, "r")
  if file then
    local model_id = file:read("*a");
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


function M.change_model()
  local text = vim.fn.system("ollama list");
  local lines = M.split_line(text);
  local best_match = nil;
  local req = vim.fn.input("Switch " .. M.MODEL .." to: ");
  local candidates = "";
  print("\n");

  for i, line in ipairs(lines) do
    local current = line:gmatch("[^ ]+")();
    if i ~= 1 and current ~= nil then
      if #candidates ~= 0 then
        candidates = candidates .. ", "
      end
      candidates = candidates .. current
      if req ~= "" and line:match(req) then
        if best_match ~= nil then
          print("Too many models match " .. req .. ": "..best_match .. ", " .. current)
          return
        end
        best_match = current
      end
    end
  end
  if best_match == nil or req == "" then
    if req ~= "" then
      print("Unable to match " .. req .. ". Models: "..candidates)
    else
      print("Models: "..candidates)
    end
    return
  end
  print("Matched request " .. req .. " to " .. best_match .. ". Switched.");
  M.MODEL = best_match;
  vim.g.MAGICAIC_MODEL = M.MODEL;
  M.save_model_id()
end

function M.do_send(is_chat, prompt)
  local generation_mode = "raw";
  if is_chat then 
    generation_mode = "chat";
  end
  return vim.fn.system({"ollama-query.py", M.MODEL, generation_mode, prompt});
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
    new_content = M.split_line(new_content);
  end
  M.clear_buffer(buffer_id);
  vim.api.nvim_buf_set_text(buffer_id, 0,0, 0,0, new_content);
end

function M.general_quick_ask()
  local q = vim.fn.input("Contextless: ");
  if q == "" then
    print("(cancelled)")
    return;
  end
  q = "<USER>" .. q .. "\n<AI>";
  local text = M.do_send(true, q);
  local buf = M.get_buffer();
  M.replace_buffer_content(buf, q.."\n"..text)
end


function M.impl_completion(is_chat)
  local buf = M.get_buffer();
  local content = vim.api.nvim_buf_get_lines(buf, 0, -1, false);
  local prompt = "";
  for line_num, text in ipairs(content) do -- table.concat eats empty lines
    if line_num ~= 1 then
      prompt = prompt .. "\n";
    end
    prompt = prompt .. text;
  end
  local text = M.do_send(is_chat, prompt);
  if is_chat then
    text = "\n<AI>: " .. text
  end

  M.replace_buffer_content(buf, prompt..text)
end

function M.general_completion()
  return M.impl_completion(false);
end

function M.chat_completion()
  return M.impl_completion(true);
end

function M.show_buffer(buffer_id)
  local wins = vim.api.nvim_list_wins();
  -- CHECK IF IT EXISTS
  for _, win_id in ipairs(wins) do
    local win_buf = vim.api.nvim_win_get_buf(win_id);
    if win_buf == buffer_id then
      return;
    end;
  end

  -- SPLIT
  vim.cmd (tostring(VIEW_HEIGHT) .. "split")
  vim.cmd ("buffer " .. tostring(buffer_id))
  vim.cmd ("setf markdown")
end

function M.get_buffer()
  if M.buffer_id ~= nil and not vim.api.nvim_buf_is_valid(M.buffer_id) then
    M.buffer_d = nil;
  end

  if M.buffer_id == nil then
    M.buffer_id = vim.api.nvim_create_buf(true, true);
    vim.api.nvim_buf_set_name(M.buffer_id, "Magaic");
  end

  M.show_buffer(M.buffer_id);

  return M.buffer_id
end

function M.display_buffer()
  M.get_buffer()
end

-- M.general_quick_ask() -- REPLACES ALL CONTENT 
-- M.general_completion() -- APPEND TO CONTENT
-- M.display_buffer () -- DISPLAY BUFFER
return M
