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
//#pragma target("avx2")
//#pragma ivdep
#define fi first
#define pi pair <long long, long long>
#define se second
using namespace std;
typedef long long ll;
 
const ll maxN = 1e5 + 2;
vector <ll> g[maxN] = { {} };
unordered_set <ll> ans[maxN] = { {} };
bool used[maxN] = { 0 };
ll c[maxN] = { 0 };
void dfs(ll v) {
	used[v] = 1;
	for (ll u : g[v]) {
		if (c[v] != c[u]) {
			ans[c[v]].insert(c[u]);
			ans[c[u]].insert(c[v]);
		}
		if (!used[u]) {
			dfs(u);
		}
	}
}
 
void solve()
{
	ll n, m; cin >> n >> m;
	for (ll i = 0; i < n; i++) {
		cin >> c[i];
	}
	for (ll i = 0; i < m; i++) {
		ll u, v; cin >> u >> v; u--; v--;
		g[u].push_back(v);
		g[v].push_back(u);
	}
 
	for (int i = 0; i < n; i++) {
		dfs(i);
	}
	ll Max = -1, idxans = 0;
	for (ll i = 0; i < n; i++) {
		if (Max < (int)ans[c[i]].size() || (Max == (int)ans[c[i]].size() && idxans > c[i])) {
			Max = (int)ans[c[i]].size();
			idxans = c[i];
		}
	}
 
	cout << idxans;
}
signed main()
{
	ios_base::sync_with_stdio(0);
	cin.tie(0);
	cout.tie(0);
 
	long long T = 1;
	while (T--)
	{
		solve();
	}
 
	return 0;
 
}