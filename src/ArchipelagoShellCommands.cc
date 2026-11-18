// Archipelago shell commands. The AP client sends these over the HTTP API (/y/shell-exec).
#include <format>
#include <functional>
#include <map>
#include <phosg/Strings.hh>
#include <stdexcept>

#include "Archipelago.hh"
#include "Lobby.hh"
#include "SendCommands.hh"
#include "ServerState.hh"
#include "ShellCommands.hh"

namespace {

struct APSetting {
  std::function<std::string(ServerState&)> get;
  std::function<void(ServerState&, const std::string&)> set;
};

float parse_multiplier(const std::string& v) {
  float f = std::stof(v);
  if (!(f > 0.0f)) {
    throw std::runtime_error("multiplier must be positive");
  }
  return f;
}

// Keys match the apworld's slot_data keys. Values are runtime-only: a restart (or `reload config`, for settings
// newserv's config also has) resets them.
const std::map<std::string, APSetting>& ap_settings() {
  static const std::map<std::string, APSetting> ret = {
      {"exp_multiplier", {
                             [](ServerState& s) { return std::format("{}", s.data->bb_global_exp_multiplier); },
                             [](ServerState& s, const std::string& v) {
                               float mult = parse_multiplier(v);
                               s.data->bb_global_exp_multiplier = mult; // new games copy this at creation
                               // Running games too: the server computes EXP from the game's copy, and 6xDD updates
                               // what the client displays (it's also sent when a client joins).
                               for (const auto& [_, l] : s.id_to_lobby) {
                                 if (l->is_game()) {
                                   l->base_exp_multiplier = mult;
                                   send_set_exp_multiplier(l);
                                 }
                               }
                             },
                         }},
      {"money_multiplier", {
                                [](ServerState&) { return std::format("{}", ap_money_multiplier); },
                                [](ServerState&, const std::string& v) { ap_money_multiplier = parse_multiplier(v); },
                            }},
  };
  return ret;
}

ShellCommand c_ap_set(
    "ap-set", "ap-set [KEY [VALUE]]\n\
    Archipelago slot setting. No arguments lists all; KEY alone shows one.\n\
    Settings reset on restart. Changes apply immediately, including to games\n\
    already running.",
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
