#include <iostream>
#include <vector>
#include <algorithm>
#include <string>
#include <cmath>
#include <queue>
#include <unordered_set>
#include <unordered_map>
constexpr auto INF = 1000000000;

using namespace std;

int n, m;
vector < vector <int> > graph;
vector < unordered_map <int, bool> > bridge;
vector <int> tin, tup, color;
int timer;

void dfs(int v, int p)
{
	color[v] = 1;
	timer++;
	tin[v] = tup[v] = timer;
	for (int u : graph[v])
	{
		if (color[u] == 0)
		{
			dfs(u, v);
			tup[v] = min(tup[v], tup[u]);
			if (tup[u] > tin[v])
			{
				bridge[v][u] = bridge[u][v] = true;
			}
		}
		else if (color[u] == 1 and p != u)
		{
			tup[v] = min(tup[v], tin[u]);
		}
	}
	color[v] = 2;
}

int main()
{
	cin >> n >> m;
	timer = 0;
	tup.assign(n, INF);
	tin.assign(n, 0);
	color.assign(n, 0);
	graph.resize(n);
	bridge.resize(n);

	for (int i = 0; i < m; i++)
	{
		int a, b; cin >> a >> b; a--; b--;
		bridge[a][b] = false;
		bridge[b][a] = false;
		graph[a].push_back(b);
		graph[b].push_back(a);
	}

	dfs(0, -1);

	int ans = 0;
	for (int i = 0; i < n; i++)
		for(int u : graph[i])
			if (!bridge[i][u]) ans++;

	cout << ans / 2 << endl; // edges repeat twice, so we divide ans by 2.

	return 0;
}