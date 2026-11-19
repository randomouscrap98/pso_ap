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
      // Read live wherever the name is shown (menus, messages, mail), so it applies immediately
      {"server_name", {
                          [](ServerState& s) { return s.data->name; },
                          [](ServerState& s, const std::string& v) { s.data->name = v; },
                      }},
  };
  return ret;
}

ShellCommand c_ap_set(
    "ap-set", "ap-set [KEY [VALUE]]\n\
    Archipelago slot setting. No arguments lists all; KEY alone shows one.\n\
    VALUE is the rest of the line, so it may contain spaces.\n\
    Settings reset on restart. Changes apply immediately, including to games\n\
    already running.",
    +[](ShellCommand::Args& args) -> asio::awaitable<std::deque<std::string>> {
      std::string key = args.args;
      phosg::strip_whitespace(key);
      std::string value;
      if (size_t space = key.find(' '); space != std::string::npos) {
        value = key.substr(space + 1);
        phosg::strip_whitespace(value);
        key.resize(space);
      }
      std::deque<std::string> ret;
      if (key.empty()) {
        for (const auto& [k, setting] : ap_settings()) {
          ret.emplace_back(std::format("{} = {}", k, setting.get(*args.s)));
        }
        co_return ret;
      }
      auto it = ap_settings().find(key);
      if (it == ap_settings().end()) {
        throw std::runtime_error("unknown setting: " + key);
      }
      if (!value.empty()) {
        try {
          it->second.set(*args.s, value);
        } catch (const std::invalid_argument&) {
          throw std::runtime_error("invalid value: " + value);
        }
      }
      ret.emplace_back(std::format("{} = {}", it->first, it->second.get(*args.s)));
      co_return ret;
    });

} // namespace
