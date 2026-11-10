#include <algorithm>
#include <bitset>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <queue>
#include <random>
#include <set>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#define pi pair<long long, long long>
using namespace std;
typedef long long ll;
 
void solve() {
  ll n, m, s;
  cin >> n >> m >> s;
  ll e, k;
  cin >> e >> k;
  ll b = 0;
  for (ll i = 0; i < s; i++) {
    b = b - ((b / m) * min(e, m) + min(b % m, e));
    b = min(n * m, b + k);
  }
  ll end = max(0ll, b - (n - 1) * m);
  if (end == m) {
    cout << 1 << ' ' << m << endl;
  } else {
    ll last = b % m;
    ll full_cnt = b / m;
    if (full_cnt == n - 1)
      cout << n << " " << end;
    else {
      cout << b / m + (b % m > 0) + 1 << " " << end;
    }
  }
}
 
signed main() {
  ios_base::sync_with_stdio(0);
  cin.tie(0);
  cout.tie(0);
  ll t = 1;
  while (t--) {
    solve();
  }
  return 0;
}