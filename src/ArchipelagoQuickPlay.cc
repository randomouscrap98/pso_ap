// Archipelago quick play: start a solo game from the main menu instead of the lobby's team counter.
// Flow: main menu "Quick play" -> episode menu -> difficulty menu -> "Go to lobby" with Client::ap_quick_play set ->
// on arrival in the lobby (6x23), create a solo game and move the client into it (the same steps as the C1 handler).
#include <format>
#include <stdexcept>

#include "Archipelago.hh"
#include "Client.hh"
#include "Lobby.hh"
#include "Menu.hh"
#include "ReceiveCommands.hh"
#include "ServerState.hh"

namespace {

// Item IDs: episode menu = 0xDD0E00DD | episode << 8; difficulty menu also carries the difficulty in the low nibble
// of the third byte, so the choice needs no state between the two menus.
constexpr uint32_t EPISODE_ITEM_BASE = 0xDD0E00DD;
constexpr uint32_t DIFFICULTY_ITEM_BASE = 0xDD0D00DD;
constexpr Episode EPISODES[] = {Episode::EP1, Episode::EP2, Episode::EP4};
constexpr Difficulty DIFFICULTIES[] = {Difficulty::NORMAL, Difficulty::HARD, Difficulty::VERY_HARD, Difficulty::ULTIMATE};

uint32_t episode_item_id(Episode episode) {
  return EPISODE_ITEM_BASE | (static_cast<uint32_t>(episode) << 8);
}

uint32_t difficulty_item_id(Episode episode, Difficulty difficulty) {
  return DIFFICULTY_ITEM_BASE | (static_cast<uint32_t>(episode) << 12) | (static_cast<uint32_t>(difficulty) << 8);
}

Episode checked_episode(uint32_t value) {
  for (Episode episode : EPISODES) {
    if (static_cast<uint32_t>(episode) == value) {
      return episode;
    }
  }
  throw std::runtime_error(std::format("invalid quick play episode {}", value));
}

} // namespace

std::shared_ptr<const Menu> ap_quick_play_episode_menu() {
  auto menu = std::make_shared<Menu>(MenuID::AP_QUICK_PLAY_EPISODE, "Quick play");
  menu->items.emplace_back(AP_QUICK_PLAY_GO_BACK, "Go back", "Return to the\nmain menu", 0);
  for (Episode episode : EPISODES) {
    menu->items.emplace_back(episode_item_id(episode), name_for_episode(episode),
        std::format("Start a solo game\nin {}", name_for_episode(episode)), 0);
  }
  return menu;
}

std::shared_ptr<const Menu> ap_quick_play_difficulty_menu(std::shared_ptr<const Client> c, Episode episode) {
  auto s = c->require_server_state();
  auto p = c->character_file();
  bool free_join = c->login->account->check_flag(Account::Flag::FREE_JOIN_GAMES);

  auto menu = std::make_shared<Menu>(MenuID::AP_QUICK_PLAY_DIFFICULTY, name_for_episode(episode));
  menu->items.emplace_back(AP_QUICK_PLAY_GO_BACK, "Go back", "Choose a different\nepisode", 0);
  for (Difficulty difficulty : DIFFICULTIES) {
    // Same level requirement create_game_generic enforces; listing only what's allowed avoids a refusal after the
    // client has already gone to the lobby
    size_t min_level = s->data->default_min_level_for_game(c->version(), episode, difficulty);
    if (free_join || min_level <= p->disp.stats.level) {
      menu->items.emplace_back(difficulty_item_id(episode, difficulty), name_for_difficulty(difficulty),
          std::format("Start a solo game\nin {}\non {}", name_for_episode(episode), name_for_difficulty(difficulty)), 0);
    }
  }
  return menu;
}

Episode ap_quick_play_episode(uint32_t episode_item_id) {
  if ((episode_item_id & 0xFFFF00FF) != EPISODE_ITEM_BASE) {
    throw std::runtime_error("invalid quick play episode item");
  }
  return checked_episode((episode_item_id >> 8) & 0xFF);
}

std::pair<Episode, Difficulty> ap_quick_play_choice(uint32_t difficulty_item_id) {
  if ((difficulty_item_id & 0xFFFF00FF) != DIFFICULTY_ITEM_BASE) {
    throw std::runtime_error("invalid quick play difficulty item");
  }
  uint32_t difficulty = (difficulty_item_id >> 8) & 0x0F;
  if (difficulty > static_cast<uint32_t>(Difficulty::ULTIMATE)) {
    throw std::runtime_error("invalid quick play difficulty");
  }
  return {checked_episode((difficulty_item_id >> 12) & 0x0F), static_cast<Difficulty>(difficulty)};
}

void ap_on_lobby_arrival(std::shared_ptr<Client> c) {
  if (!c->ap_quick_play) {
    return;
  }
  auto [episode, difficulty] = *c->ap_quick_play;
  c->ap_quick_play.reset(); // one attempt: on failure the player just stays in the lobby
  auto s = c->require_server_state();
  std::string name = c->character_file()->disp.visual.name.decode(c->language());
  // Sends the player a message box and returns null if it can't create the game
  auto game = create_game_generic(s, c, name, "", episode, GameMode::SOLO, difficulty);
  if (game) {
    s->change_client_lobby(c, game);
    c->set_flag(Client::Flag::LOADING);
    c->log.info_f("LOADING flag set (quick play)");
  }
}
