#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_set>
#include <unordered_map>
#include <queue>
#include <deque>
#include <map>
#include <set>
#include <cmath>
#include <random>
#include <bitset>
#include <string>
#include <iomanip>
#include <ext/pb_ds/tree_policy.hpp>
#include <ext/pb_ds/assoc_container.hpp>
#pragma GCC target("avx2")
#define fi first
#define pi pair <long long, long long>
#define se second

using namespace std;
namespace __gnu_pbds{
          typedef tree<int,
                       null_type,
                       less_equal<int>,
                       rb_tree_tag,
                       tree_order_statistics_node_update> ordered_set;
}

using namespace __gnu_pbds;
typedef long long ll;

void solve()
{
	int n; cin >> n;
	vector <int> arr(n);
	for (int i = 0; i < n; i++) cin >> arr[i];
	ordered_set st;
	ll ans = 0;
	for (int i = 0; i < n; i++)
	{
        auto it = st.lower_bound(arr[i]);
        if (it != st.end()) ans += st.size() - st.order_of_key(*it);
		st.insert(arr[i]);
	}

	cout << ans << '\n';
}   

signed main()
{
	ios_base::sync_with_stdio(0);
	cin.tie(0);
	cout.tie(0);

	long long tcnt; cin >> tcnt;
	while (tcnt--)
	{
		solve();
	}

	return 0;

}