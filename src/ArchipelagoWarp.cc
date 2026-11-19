// Archipelago $goto: warp from Pioneer 2 to any floor reached before on this seed, so a crash or logoff doesn't mean
// walking an area again. Reached floors are per episode and difficulty, shared by everyone on this server (one newserv
// per AP slot), and saved in the seed's data directory.
#include <format>
#include <map>
#include <phosg/Filesystem.hh>
#include <phosg/JSON.hh>
#include <set>
#include <string>

#include "Archipelago.hh"
#include "Client.hh"
#include "Lobby.hh"
#include "Loggers.hh"
#include "SendCommands.hh"
#include "StaticGameData.hh"
#include "UserDataDirectory.hh"

namespace {

// Key: "<episode>/<difficulty>" token names, e.g. "Episode1/Normal"; value: floor numbers within the episode
using ReachedFloors = std::map<std::string, std::set<uint8_t>>;

std::string reached_floors_filename() {
  return user_data_dir + "/ap_reached_floors.json";
}

std::string reached_key(const Lobby& l) {
  return std::format("{}/{}", token_name_for_episode(l.episode), token_name_for_difficulty(l.difficulty));
}

ReachedFloors& reached_floors() {
  static ReachedFloors floors = []() {
    ReachedFloors ret;
    std::string filename = reached_floors_filename();
    if (!std::filesystem::is_regular_file(filename)) {
      return ret;
    }
    try {
      auto json = phosg::JSON::parse(phosg::load_file(filename));
      for (const auto& [key, list] : json.as_dict()) {
        auto& floors = ret[key];
        for (const auto& floor : list->as_list()) {
          floors.emplace(floor->as_int());
        }
      }
    } catch (const std::exception& e) {
      server_log.warning_f("Cannot load {}: {}", filename, e.what());
    }
    return ret;
  }();
  return floors;
}

void save_reached_floors() {
  auto json = phosg::JSON::dict();
  for (const auto& [key, floors] : reached_floors()) {
    auto list = phosg::JSON::list();
    for (uint8_t floor : floors) {
      list.emplace_back(floor);
    }
    json.emplace(key, std::move(list));
  }
  phosg::save_file(reached_floors_filename(), json.serialize(phosg::JSON::SerializeOption::FORMAT));
}

// Floors that can be reached and warped to outside quests: not cities, lobbies or the test map (drop area 0xFF)
bool is_warpable(const FloorDefinition& def) {
  return !(def.flags & (FloorDefinition::Flag::CITY | FloorDefinition::Flag::LOBBY)) && (def.drop_area_norm != 0xFF);
}

// Free play only: quests remap floors to other areas, and battle/challenge games have their own floors
bool is_free_play(const Lobby& l) {
  return ((l.mode == GameMode::NORMAL) || (l.mode == GameMode::SOLO)) &&
      !l.check_flag(Lobby::Flag::QUEST_IN_PROGRESS) &&
      !l.check_flag(Lobby::Flag::JOINABLE_QUEST_IN_PROGRESS);
}

const FloorDefinition* floor_def(Episode episode, uint32_t floor) {
  if (floor >= FloorDefinition::limit_for_episode(episode)) {
    return nullptr;
  }
  return &FloorDefinition::get(episode, floor);
}

std::string reached_floors_text(const Lobby& l) {
  std::string ret;
  auto it = reached_floors().find(reached_key(l));
  if (it != reached_floors().end()) {
    for (uint8_t floor : it->second) {
      ret += std::format("{}{}", ret.empty() ? "" : " ", FloorDefinition::get(l.episode, floor).short_name);
    }
  }
  return ret;
}

} // namespace

void ap_on_floor_change(std::shared_ptr<Client> c) {
  auto l = c->lobby.lock();
  if (!l || !l->is_game() || !is_free_play(*l)) {
    return;
  }
  const auto* def = floor_def(l->episode, c->floor);
  if (!def || !is_warpable(*def)) {
    return;
  }
  if (reached_floors()[reached_key(*l)].emplace(c->floor).second) {
    c->log.info_f("Reached {} for the first time on this seed", def->in_game_name);
    save_reached_floors();
  }
}

void ap_goto(std::shared_ptr<Client> c, const std::string& args) {
  auto l = c->lobby.lock();
  if (!l || !l->is_game()) {
    send_text_message(c, "$C6Use $goto in a game");
    return;
  }
  if (!is_free_play(*l)) {
    send_text_message(c, "$C6$goto doesn't work\nin quests or\nbattle/challenge");
    return;
  }
  std::string reached = reached_floors_text(*l);
  if (args.empty()) {
    send_text_message(c, reached.empty() ? "$C6No floors reached yet" : ("$C6Reached floors:\n" + reached));
    return;
  }
  const auto* city = floor_def(l->episode, c->floor);
  if (!city || !(city->flags & FloorDefinition::Flag::CITY)) {
    send_text_message(c, "$C6Use $goto from\nPioneer 2");
    return;
  }

  const FloorDefinition* target = nullptr;
  try {
    size_t end;
    unsigned long number = std::stoul(args, &end, 0);
    target = (end == args.size()) ? floor_def(l->episode, number) : nullptr;
  } catch (const std::exception&) {
    try {
      target = &FloorDefinition::get(l->episode, args);
    } catch (const std::out_of_range&) {
    }
  }
  const auto& floors = reached_floors()[reached_key(*l)];
  if (!target || !floors.contains(target->floor)) {
    send_text_message(c, reached.empty() ? "$C6No floors reached yet" : ("$C6Not reached. Reached:\n" + reached));
    return;
  }
  send_warp(c, target->floor, true);
}
