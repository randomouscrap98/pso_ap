#pragma once

#include <algorithm>
#include <asio.hpp>
#include <cmath>
#include <cstdint>
#include <memory>
#include <string>
#include <utility>

#include "StaticGameData.hh"

class AccountIndex;
class Client;
struct DataIndex;
struct Menu;

// Archipelago slot settings that upstream newserv has no config for. Server-wide (one newserv per AP slot); set by
// `ap-set` (ArchipelagoShellCommands.cc), runtime only.
inline float ap_money_multiplier = 1.0f;

// Meseta the player receives (enemy/box drops, quest rewards) after the slot's multiplier, capped at max_amount
inline uint32_t ap_scale_meseta(uint32_t amount, uint32_t max_amount) {
  double scaled = std::round(amount * static_cast<double>(ap_money_multiplier));
  return static_cast<uint32_t>(std::min<double>(scaled, max_amount));
}

// Mag feeding (ArchipelagoMags.cc). Simple: one flat feed table for every mag form, where each item raises one stat;
// the multiplier scales those stat gains (each capped at 127, the client's limit). Vanilla ignores the multiplier.
inline bool ap_simple_mag_feeding = false;
inline int ap_mag_feed_multiplier = 1;
// Rebuilds BB's item parameter table and stream file from the two settings above
void ap_apply_mag_feeding(DataIndex& data);

// Singleplayer mode (ArchipelagoSingleplayer.cc; --singleplayer, set by the AP client from host.yaml). Every BB login
// uses the seed's one solo account, and quick play makes Solo games (otherwise Normal games, which friends can join).
inline bool ap_singleplayer = false;
// Replaces a BB login's credentials with the solo account's (no-op unless singleplayer, or before the first account)
void ap_singleplayer_credentials(AccountIndex& accounts, std::string& username, std::string& password);

// Quick play (ArchipelagoQuickPlay.cc): main menu -> episode -> difficulty -> a game, without the team counter.
// The client goes to the lobby as usual; the game is created once it has arrived there (6x23), because the client
// only accepts a game join from the lobby.
constexpr uint32_t AP_QUICK_PLAY_GO_BACK = 0xDDFFFFDD; // item ID in both quick play menus
std::shared_ptr<const Menu> ap_quick_play_episode_menu();
// Only the difficulties the character's level allows
std::shared_ptr<const Menu> ap_quick_play_difficulty_menu(std::shared_ptr<const Client> c, Episode episode);
Episode ap_quick_play_episode(uint32_t episode_item_id);
std::pair<Episode, Difficulty> ap_quick_play_choice(uint32_t difficulty_item_id);
// Called when a client has arrived in a lobby; creates and joins its pending quick play game, if any
asio::awaitable<void> ap_on_lobby_arrival(std::shared_ptr<Client> c);

// $goto (ArchipelagoWarp.cc): warp from Pioneer 2 to a floor reached before on this seed (per episode and difficulty,
// saved in the seed's data directory). Called after a client's floor changes, to record reached floors
void ap_on_floor_change(std::shared_ptr<Client> c);
// Handles "$goto [floor]": no argument lists reached floors; replies to the client itself
void ap_goto(std::shared_ptr<Client> c, const std::string& args);
// Quest counter version (BB): a "Return to a floor" entry in the quest category menu (AP_GOTO_CATEGORY), which opens
// a quest-style list of reached floors (AP_GOTO_FLOOR, item ID = floor); choosing one warps instead of loading a quest
constexpr const char* AP_GOTO_MENU_NAME = "Return to a floor";
constexpr const char* AP_GOTO_MENU_DESCRIPTION = "Warp to a floor already\nreached on this seed.";
bool ap_goto_menu_available(std::shared_ptr<Client> c);
void ap_goto_send_floor_menu(std::shared_ptr<Client> c);
void ap_goto_menu_select(std::shared_ptr<Client> c, uint32_t floor);
