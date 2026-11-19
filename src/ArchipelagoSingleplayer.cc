// Archipelago singleplayer mode (--singleplayer, from the AP client's host.yaml): every BB login on this server uses
// one account, whatever username and password the game sends, so the player never has to think about logins and
// always finds the same characters. The solo account is an existing BB account if the seed has any (the one with the
// lowest account ID, so the choice is stable across restarts; a solo seed normally has exactly one); otherwise the
// first login's own credentials create it as usual.
#include <string>

#include "Account.hh"
#include "Archipelago.hh"
#include "Loggers.hh"

void ap_singleplayer_credentials(AccountIndex& accounts, std::string& username, std::string& password) {
  if (!ap_singleplayer) {
    return;
  }
  std::shared_ptr<const Account> solo;
  for (const auto& a : accounts.all()) {
    if (!a->is_temporary && !a->bb_licenses.empty() && (!solo || a->account_id < solo->account_id)) {
      solo = a;
    }
  }
  if (!solo) {
    return; // first login on this seed: it creates the solo account
  }
  // An account can hold several BB licenses; pick the smallest username, again for a stable choice
  std::shared_ptr<const BBLicense> lic;
  for (const auto& [_, l] : solo->bb_licenses) {
    if (!lic || l->username < lic->username) {
      lic = l;
    }
  }
  if (username != lic->username) {
    client_log.info_f("Singleplayer: login as {} uses the solo account ({})", username, lic->username);
  }
  username = lic->username;
  password = lic->password;
}
