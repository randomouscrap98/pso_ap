// Archipelago shell commands. The AP client sends these over the HTTP API (/y/shell-exec).
#include <format>
#include <functional>
#include <map>
#include <phosg/Strings.hh>
#include <stdexcept>

#include "ShellCommands.hh"

namespace {

struct APSetting {
  std::function<std::string(ServerState&)> get;
  std::function<void(ServerState&, const std::string&)> set;
};

// Keys match the apworld's slot_data keys. Values are runtime-only: a restart or `reload config` resets them.
const std::map<std::string, APSetting>& ap_settings() {
  static const std::map<std::string, APSetting> ret = {
      {"exp_multiplier", {
                             [](ServerState& s) { return std::format("{}", s.data->bb_global_exp_multiplier); },
                             [](ServerState& s, const std::string& v) {
                               float f = std::stof(v);
                               if (!(f > 0.0f)) {
                                 throw std::runtime_error("exp_multiplier must be positive");
                               }
                               s.data->bb_global_exp_multiplier = f; // games copy this at creation
                             },
                         }},
  };
  return ret;
}

ShellCommand c_ap_set(
    "ap-set", "ap-set [KEY [VALUE]]\n\
    Archipelago slot setting. No arguments lists all; KEY alone shows one.\n\
    Settings apply to games created afterward and reset on restart.",
    +[](ShellCommand::Args& args) -> asio::awaitable<std::deque<std::string>> {
      auto tokens = phosg::split(args.args, ' ');
      std::erase(tokens, "");
      std::deque<std::string> ret;
      if (tokens.empty()) {
        for (const auto& [key, setting] : ap_settings()) {
          ret.emplace_back(std::format("{} = {}", key, setting.get(*args.s)));
        }
        co_return ret;
      }
      auto it = ap_settings().find(tokens[0]);
      if (it == ap_settings().end()) {
        throw std::runtime_error("unknown setting: " + tokens[0]);
      }
      if (tokens.size() > 2) {
        throw std::runtime_error("usage: ap-set [KEY [VALUE]]");
      }
      if (tokens.size() == 2) {
        try {
          it->second.set(*args.s, tokens[1]);
        } catch (const std::invalid_argument&) {
          throw std::runtime_error("invalid value: " + tokens[1]);
        }
      }
      ret.emplace_back(std::format("{} = {}", it->first, it->second.get(*args.s)));
      co_return ret;
    });

} // namespace
