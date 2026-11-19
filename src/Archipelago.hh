#pragma once

#include <algorithm>
#include <asio.hpp>
#include <cmath>
#include <cstdint>
#include <memory>
#include <utility>

#include "StaticGameData.hh"

class Client;
struct Menu;

// Archipelago slot settings that upstream newserv has no config for. Server-wide (one newserv per AP slot); set by
// `ap-set` (ArchipelagoShellCommands.cc), runtime only.
inline float ap_money_multiplier = 1.0f;

// Meseta the player receives (enemy/box drops, quest rewards) after the slot's multiplier, capped at max_amount
inline uint32_t ap_scale_meseta(uint32_t amount, uint32_t max_amount) {
  double scaled = std::round(amount * static_cast<double>(ap_money_multiplier));
  return static_cast<uint32_t>(std::min<double>(scaled, max_amount));
}

// Quick play (ArchipelagoQuickPlay.cc): main menu -> episode -> difficulty -> a solo game, without the team counter.
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
