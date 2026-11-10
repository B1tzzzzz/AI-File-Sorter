#include <vector>
#include <algorithm>
#include <set>
#include <unordered_set>
#include <unordered_map>
#include <queue>
#include <map>
#include <cmath>
#include <random>
#include <bitset>
#include <string>
#include <iostream>
#include <iomanip>
#include <cstring>
#define fi first
#define pi pair <long long, long long>
#define se second
using namespace std;
typedef long long ll;

const ll INF = 2e9, maxTN = (1 << 4), maxN = 1e5 + 1, mod = 1e9 + 7;

vector <ll> g[maxN] = { {} };
bool used[maxN] = { 0 };
ll ans[maxN] = { 0 }, sz[maxN] = { 0 };

ll bpow(ll n) {
	if (n == 0) return 1;
	if (n % 2) return 2 * bpow(n - 1) % mod;
	return bpow(n / 2) * bpow(n / 2) % mod;
}

int s = 0;
void dfs(ll v) {
	used[v] = 1;
	sz[v] = 1;
	ll v0 = 1;
	for (ll u : g[v]) {
		if (used[u]) continue;
		dfs(u);
		v0 += bpow(sz[u]) - 1;
		v0 %= mod;
		ans[v] += ans[u];
		ans[v] %= mod;
		sz[v] += sz[u];
	}
	ans[v] += (v + 1) * bpow(sz[v] - 1);
	ans[v] %= mod;
	if (g[v].size() > 2 || (g[v].size() == 2 && s == v)) {
		int diff = bpow(sz[v] - 1) - v0;
		if (diff < 0) diff += mod;
		ans[v] += (v + 1) * diff;
	}
		
	ans[v] %= mod;
}
void solve()
{
	ll n; cin >> n;
	memset(ans, 0, sizeof(ans));
	memset(sz, 0, sizeof(sz));
	for (ll i = 0; i < n; i++) {
		g[i].clear();
	}

	for (ll i = 0; i < n; i++) {
		used[i] = 0;
		ll v; cin >> v; v--;
		if (i == v) {
			s = i;
			continue;
		}
		g[v].push_back(i);
		g[i].push_back(v);
	}

	dfs(s);
	cout << ans[s] << '\n';

}

signed main()
{
	ios_base::sync_with_stdio(0);
	cin.tie(0);
	cout.tie(0);

	long long T; cin >> T;
	while (T--)
	{
		solve();
	}

	return 0;

}

/*
8
1 8 2 6 3 7 4 5*/