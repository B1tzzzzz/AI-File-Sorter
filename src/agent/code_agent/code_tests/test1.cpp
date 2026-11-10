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

const int maxN = 333335, maxA = maxN * 33 + 1, maxK = 280, mod = 333333333;
int a[maxN] = { 0 }, dp[maxN] = { 0 };

bool dplr[maxN][maxK] = { {0} }, p[maxA] = { 0 };

void build() {
	for (int i = 0; i * i < maxA; i++) {
		p[i] = 1;
	}
	p[0] = 0;
	p[1] = 0;
	for (int i = 2; i * i < maxA; i++) {
		for (int j = i * i; j < maxA; j += i) {
			p[j] = 0;
		}
	}
}
void solve()
{
	build();
	int n; cin >> n;
	for (int i = 0; i < n; i++) {
		cin >> a[i];
	}

	for (int i = 0; i < n; i++) {
		dplr[i][0] = 1;
	}

	for (int r = 1; r < maxK; r++) {
		int sum = 0;
		for (int i = 0; i <= r; i++) {
			sum += a[i];
		}
		for (int l = 0; l < n; l++) {
			if (l + r >= n) break;
			if (!p[sum]) {
				sum += a[l + r + 1] - a[l];
				continue;
			}
			sum += a[l + r + 1] - a[l];
			dplr[l][r] = dplr[l + 1][r - 1] | dplr[l][r - 1];
			dplr[l][r] |= dplr[l + 2][r - 2] & (a[l] == a[l + 1]) & (a[l + 1] == 1);
			dplr[l][r] |= dplr[l][r - 2] & (a[l + r] == a[l + r - 1]) & (a[l + r - 1] == 1);
		}
	}

	dp[0] = 1;
	for (int i = 1; i < n + 1; i++) {
		dp[i] = dp[i - 1];
		for (int j = max(0, i - maxK); j < i - 1; j++) {
			dp[i] += (dplr[j][i - j - 1] ? dp[j] : 0);
			if (dp[i] >= mod) dp[i] -= mod;
		}
	}
	cout << dp[n];
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
/*
14
1 3 2 3 2 1 2 2 1 1 2 3 2 3*/