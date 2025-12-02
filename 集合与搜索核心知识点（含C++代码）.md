# 集合与搜索核心知识点（含C++代码）

## 一、集合及其表示

### 核心概念

- 集合：由互不相同元素构成的整体，支持并、交、差、查找、插入、删除等操作。

- 两种核心实现方式：位向量（适用于元素为连续整数的场景）、有序链表（适用于元素离散的场景）。

### C++ 代码实现

#### 1. 位向量实现集合 ADT

```cpp

#include <vector>
#include <iostream>
using namespace std;

class BitSetSet {
private:
    vector<bool> bits; // 位向量存储，bit[i]为true表示元素i存在
    int maxElem; // 集合中最大可能元素值
public:
    BitSetSet(int maxE) : maxElem(maxE), bits(maxE + 1, false) {}

    // 插入元素x
    void insert(int x) {
        if (x >= 0 && x <= maxElem) bits[x] = true;
    }

    // 删除元素x
    void remove(int x) {
        if (x >= 0 && x <= maxElem) bits[x] = false;
    }

    // 查找元素x是否存在
    bool search(int x) {
        if (x < 0 || x > maxElem) return false;
        return bits[x];
    }

    // 集合交集
    BitSetSet intersect(const BitSetSet& other) {
        BitSetSet res(min(maxElem, other.maxElem));
        for (int i = 0; i <= res.maxElem; ++i) {
            res.bits[i] = bits[i] && other.bits[i];
        }
        return res;
    }

    // 集合并集
    BitSetSet unite(const BitSetSet& other) {
        BitSetSet res(max(maxElem, other.maxElem));
        for (int i = 0; i <= res.maxElem; ++i) {
            res.bits[i] = (i <= maxElem ? bits[i] : false) || (i <= other.maxElem ? other.bits[i] : false);
        }
        return res;
    }
};
```

#### 2. 有序链表实现集合 ADT

```cpp

#include <iostream>
using namespace std;

struct ListNode {
    int val;
    ListNode* next;
    ListNode(int x) : val(x), next(nullptr) {}
};

class SortedListSet {
private:
    ListNode* head; // 有序链表头节点（升序）
public:
    SortedListSet() : head(nullptr) {}

    ~SortedListSet() { // 析构释放内存
        ListNode* curr = head;
        while (curr) {
            ListNode* temp = curr;
            curr = curr->next;
            delete temp;
        }
    }

    // 插入元素x（保持有序）
    void insert(int x) {
        ListNode* newNode = new ListNode(x);
        if (!head || x < head->val) { // 插入表头
            newNode->next = head;
            head = newNode;
            return;
        }
        ListNode* curr = head;
        while (curr->next && curr->next->val < x) { // 找到插入位置
            curr = curr->next;
        }
        if (curr->next && curr->next->val == x) return; // 元素已存在
        newNode->next = curr->next;
        curr->next = newNode;
    }

    // 查找元素x
    bool search(int x) {
        ListNode* curr = head;
        while (curr) {
            if (curr->val == x) return true;
            if (curr->val > x) return false; // 有序链表，后续无需查找
            curr = curr->next;
        }
        return false;
    }

    // 删除元素x
    void remove(int x) {
        if (!head) return;
        if (head->val == x) { // 删除表头
            ListNode* temp = head;
            head = head->next;
            delete temp;
            return;
        }
        ListNode* curr = head;
        while (curr->next && curr->next->val < x) {
            curr = curr->next;
        }
        if (curr->next && curr->next->val == x) { // 找到待删除节点
            ListNode* temp = curr->next;
            curr->next = curr->next->next;
            delete temp;
        }
    }
};
```

## 二、等价类与并查集

### 核心概念

- 等价关系：满足自反性、对称性、传递性的关系（如 “同属一个集合”）。

- 等价类：由等价关系划分的互不相交的子集。

- 并查集（Disjoint Set Union, DSU）：高效管理等价类的结构，支持两个核心操作：

    1. 查找（Find）：查询元素所属的等价类根节点（带路径压缩优化）。

    2. 合并（Union）：将两个等价类合并（按树高 / 大小合并，避免树退化）。

### C++ 代码实现（按树高合并 + 路径压缩）

```cpp

#include <vector>
#include <iostream>
using namespace std;

class DSU {
private:
    vector<int> parent; // parent[i]表示i的父节点
    vector<int> rank;   // rank[i]表示以i为根的树的高度
public:
    DSU(int n) { // 初始化n个元素（编号0~n-1或1~n，此处以1~n为例）
        parent.resize(n + 1);
        rank.resize(n + 1, 1); // 初始树高均为1
        for (int i = 1; i <= n; ++i) {
            parent[i] = i; // 每个元素自成一个等价类，父节点为自身
        }
    }

    // 查找x的根节点（带路径压缩）
    int find(int x) {
        if (parent[x] != x) {
            parent[x] = find(parent[x]); // 路径压缩：让x直接指向根节点
        }
        return parent[x];
    }

    // 合并x和y所在的等价类（按树高合并）
    void unite(int x, int y) {
        int rootX = find(x);
        int rootY = find(y);
        if (rootX == rootY) return; // 已在同一集合
        // 高度低的树挂到高度高的树的根节点下
        if (rank[rootX] < rank[rootY]) {
            parent[rootX] = rootY;
        } else {
            parent[rootY] = rootX;
            if (rank[rootX] == rank[rootY]) {
                rank[rootX]++; // 两树高度相等时，合并后根节点高度+1
            }
        }
    }
};
```

## 三、静态搜索表

### 核心概念

- 静态搜索：搜索表一旦建立，仅支持查找操作（不修改表结构）。

- 平均搜索长度（ASL）：所有元素查找成功的比较次数的平均值，衡量搜索效率。

- 两种核心算法：

    1. 顺序搜索：逐个遍历元素，适用于无序表，ASL=(n+1)/2（等概率）。

    2. 折半搜索（二分查找）：仅适用于有序表，ASL=log₂(n+1)-1（等概率），效率远高于顺序搜索。

### C++ 代码实现

#### 1. 顺序搜索

```cpp

#include <vector>
using namespace std;

// 在无序向量v中查找x，返回索引（-1表示未找到）
int sequentialSearch(const vector<int>& v, int x) {
    for (int i = 0; i < v.size(); ++i) {
        if (v[i] == x) return i;
    }
    return -1;
}
```

#### 2. 折半搜索

```cpp

#include <vector>
using namespace std;

// 在有序向量v（升序）中查找x，返回索引（-1表示未找到）
int binarySearch(const vector<int>& v, int x) {
    int left = 0, right = v.size() - 1;
    while (left <= right) {
        int mid = left + (right - left) / 2; // 避免溢出
        if (v[mid] == x) return mid;
        else if (v[mid] < x) left = mid + 1;
        else right = mid - 1;
    }
    return -1;
}
```

## 四、二叉搜索树（BST）

### 核心概念

- 定义：左子树所有节点值 <根节点值，右子树所有节点值> 根节点值，左右子树均为 BST。

- 核心操作：搜索、插入、删除（删除后需保持 BST 性质）。

- 中序遍历 BST 可得到有序序列。

- 平均搜索长度：理想情况下（平衡）为 O (logn)，最坏情况（退化为链表）为 O (n)。

### C++ 代码实现

```cpp

#include <iostream>
#include <vector>
using namespace std;

struct BSTNode {
    int val;
    BSTNode* left;
    BSTNode* right;
    BSTNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

class BST {
private:
    BSTNode* root;

    // 递归插入辅助函数
    BSTNode* insertHelper(BSTNode* node, int x) {
        if (!node) return new BSTNode(x);
        if (x < node->val) node->left = insertHelper(node->left, x);
        else if (x > node->val) node->right = insertHelper(node->right, x);
        return node; // x已存在，不插入
    }

    // 递归搜索辅助函数
    BSTNode* searchHelper(BSTNode* node, int x) {
        if (!node || node->val == x) return node;
        if (x < node->val) return searchHelper(node->left, x);
        else return searchHelper(node->right, x);
    }

    // 查找最小节点（用于删除右子树节点时找后继）
    BSTNode* findMin(BSTNode* node) {
        while (node->left) node = node->left;
        return node;
    }

    // 递归删除辅助函数
    BSTNode* deleteHelper(BSTNode* node, int x) {
        if (!node) return nullptr;
        // 查找待删除节点
        if (x < node->val) node->left = deleteHelper(node->left, x);
        else if (x > node->val) node->right = deleteHelper(node->right, x);
        else { // 找到待删除节点
            // 情况1：叶子节点或只有一个子节点
            if (!node->left) {
                BSTNode* temp = node->right;
                delete node;
                return temp;
            }
            if (!node->right) {
                BSTNode* temp = node->left;
                delete node;
                return temp;
            }
            // 情况2：有两个子节点，找右子树最小节点（后继）替换
            BSTNode* temp = findMin(node->right);
            node->val = temp->val;
            // 删除后继节点
            node->right = deleteHelper(node->right, temp->val);
        }
        return node;
    }

    // 中序遍历辅助函数（得到有序序列）
    void inorderHelper(BSTNode* node, vector<int>& res) {
        if (!node) return;
        inorderHelper(node->left, res);
        res.push_back(node->val);
        inorderHelper(node->right, res);
    }

public:
    BST() : root(nullptr) {}

    ~BST() { // 析构释放内存（后序遍历）
        function<void(BSTNode*)> destroy = [&](BSTNode* node) {
            if (!node) return;
            destroy(node->left);
            destroy(node->right);
            delete node;
        };
        destroy(root);
    }

    void insert(int x) { root = insertHelper(root, x); }

    bool search(int x) { return searchHelper(root, x) != nullptr; }

    void remove(int x) { root = deleteHelper(root, x); }

    vector<int> inorderTraversal() { // 中序遍历得到有序序列
        vector<int> res;
        inorderHelper(root, res);
        return res;
    }

    BSTNode* getRoot() { return root; } // 用于习题操作
};
```

## 五、AVL 树（平衡二叉搜索树）

### 核心概念

- 定义：BST 的基础上，任意节点的左右子树高度差（平衡因子）的绝对值 ≤ 1。

- 平衡化旋转：插入 / 删除后若平衡因子超标，通过 4 种旋转恢复平衡：

    1. 左单旋（LL 型）：右子树过高。

    2. 右单旋（RR 型）：左子树过高。

    3. 左右双旋（LR 型）：左子树的右子树过高。

    4. 右左双旋（RL 型）：右子树的左子树过高。

- 节点数性质：高度为 h 的 AVL 树，最少节点数 S (h) = S (h-1) + S (h-2) + 1（S (0)=0, S (1)=1）；最多节点数为 2ʰ - 1（满二叉树）。

### C++ 代码实现（核心旋转与插入）

```cpp

#include <iostream>
using namespace std;

struct AVLNode {
    int val;
    int height; // 节点高度（叶子节点高度为1）
    AVLNode* left;
    AVLNode* right;
    AVLNode(int x) : val(x), height(1), left(nullptr), right(nullptr) {}
};

class AVLTree {
private:
    AVLNode* root;

    // 获取节点高度
    int getHeight(AVLNode* node) {
        return node ? node->height : 0;
    }

    // 计算平衡因子（左子树高度 - 右子树高度）
    int getBalance(AVLNode* node) {
        return node ? getHeight(node->left) - getHeight(node->right) : 0;
    }

    // 更新节点高度
    void updateHeight(AVLNode* node) {
        node->height = max(getHeight(node->left), getHeight(node->right)) + 1;
    }

    // 右单旋（RR型）
    AVLNode* rightRotate(AVLNode* y) {
        AVLNode* x = y->left;
        AVLNode* T2 = x->right;

        // 旋转
        x->right = y;
        y->left = T2;

        // 更新高度（先更新子节点y，再更新父节点x）
        updateHeight(y);
        updateHeight(x);

        return x; // 新的根节点
    }

    // 左单旋（LL型）
    AVLNode* leftRotate(AVLNode* x) {
        AVLNode* y = x->right;
        AVLNode* T2 = y->left;

        // 旋转
        y->left = x;
        x->right = T2;

        // 更新高度
        updateHeight(x);
        updateHeight(y);

        return y; // 新的根节点
    }

    // 插入辅助函数
    AVLNode* insertHelper(AVLNode* node, int x) {
        // 1. 普通BST插入
        if (!node) return new AVLNode(x);
        if (x < node->val) node->left = insertHelper(node->left, x);
        else if (x > node->val) node->right = insertHelper(node->right, x);
        else return node; // 不允许重复元素

        // 2. 更新高度
        updateHeight(node);

        // 3. 计算平衡因子，判断是否失衡
        int balance = getBalance(node);

        // 4. 平衡化旋转
        // LL型：左子树过高，右单旋
        if (balance > 1 && x < node->left->val) {
            return rightRotate(node);
        }
        // RR型：右子树过高，左单旋
        if (balance < -1 && x > node->right->val) {
            return leftRotate(node);
        }
        // LR型：左子树的右子树过高，先左旋左子树，再右旋当前节点
        if (balance > 1 && x > node->left->val) {
            node->left = leftRotate(node->left);
            return rightRotate(node);
        }
        // RL型：右子树的左子树过高，先右旋右子树，再左旋当前节点
        if (balance < -1 && x < node->right->val) {
            node->right = rightRotate(node->right);
            return leftRotate(node);
        }

        return node; // 未失衡，返回原节点
    }

public:
    AVLTree() : root(nullptr) {}

    ~AVLTree() { // 析构释放内存
        function<void(AVLNode*)> destroy = [&](AVLNode* node) {
            if (!node) return;
            destroy(node->left);
            destroy(node->right);
            delete node;
        };
        destroy(root);
    }

    void insert(int x) { root = insertHelper(root, x); }

    AVLNode* getRoot() { return root; }
};
```

# 习题解答

## 例 1：并查集操作（按树高合并）

### 1. 并查集森林构造过程

按操作序列逐步合并，每步合并后树的结构如下（根节点标注高度）：

1. M (1,2)：1 和 2 合并，根为 1（高度 2）或 2（高度 2），此处选 1 为根（1→2）。

2. M (3,4)：3 和 4 合并，根为 3（高度 2）（3→4）。

3. M (3,5)：3 的高度 2 > 5 的高度 1，5 挂到 3 下（3→4, 3→5），根仍为 3（高度 2）。

4. M (1,7)：1 的高度 2 > 7 的高度 1，7 挂到 1 下（1→2, 1→7），根仍为 1（高度 2）。

5. M (3,6)：3 的高度 2 > 6 的高度 1，6 挂到 3 下（3→4, 3→5, 3→6），根仍为 3（高度 2）。

6. M (8,9)：8 和 9 合并，根为 8（高度 2）（8→9）。

7. M (1,8)：1 的高度 2 = 8 的高度 2，合并后根为 1（高度 3），8 挂到 1 下（1→2, 1→7, 1→8→9）。

8. M (3,10)：3 的高度 2 > 10 的高度 1，10 挂到 3 下（3→4, 3→5, 3→6, 3→10），根仍为 3（高度 2）。

9. M (3,11)：3 的高度 2 > 11 的高度 1，11 挂到 3 下（根 3，高度 2）。

10. M (3,12)：同上，12 挂到 3 下（根 3，高度 2）。

11. M (3,13)：同上，13 挂到 3 下（根 3，高度 2）。

12. M (14,15)：14 和 15 合并，根为 14（高度 2）（14→15）。

13. M (16,17)：16 和 17 合并，根为 16（高度 2）（16→17）。

14. M (14,16)：14 的高度 2 = 16 的高度 2，合并后根为 14（高度 3），16 挂到 14 下（14→15, 14→16→17）。

15. M (1,3)：1 的高度 3 > 3 的高度 2，3 挂到 1 下（1→2, 1→7, 1→8→9, 1→3→4/5/6/10/11/12/13），根为 1（高度 4）。

16. M (1,14)：1 的高度 4 > 14 的高度 3，14 挂到 1 下（1→2/7/8/3/14），根为 1（高度 4）。

最终森林只有一棵树，根为 1，所有元素均为其后代。

### 2. 存储并查集的数组（元素编号 1~17）

数组索引为元素，值为父节点（根节点父节点为自身），路径压缩前：

|元素|1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|16|17|
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
|父节点|1|1|1|3|3|3|1|1|8|3|3|3|3|1|14|14|16|
### 3. F (17) 的查找过程

1. 查找 17：父节点是 16 → 查找 16，父节点是 14 → 查找 14，父节点是 1 → 查找 1，父节点是自身（根）。

2. 路径压缩后，17、16、14 的父节点直接更新为 1，下次查找更高效。
最终 F (17) 的结果是根节点 1。

## 例 2：二分查找判定树与平均查找长度

### 1. 长度为 10 的有序表（假设元素为 1~10）的判定树

- 根节点：mid=(1+10)/2=5（第 5 个元素）。

- 左子树（1\4）：根为 mid=(1+4)/2=2；左子树（1），右子树（3\4，根为 3，右子树 4）。

- 右子树（6\10）：根为 mid=(6+10)/2=8；左子树（6\7，根为 6，右子树 7），右子树（9~10，根为 9，右子树 10）。

判定树结构（节点为元素位置，括号内为查找次数）：

```Plain Text

5(1)
      /     \
    2(2)    8(2)
   /  \    /  \
  1(3) 3(3) 6(3) 9(3)
       \    \    \
        4(4) 7(4) 10(4)
```

### 2. 等概率时查找成功的平均查找长度（ASL）

ASL = (1×1 + 2×2 + 3×4 + 4×3) / 10 = (1 + 4 + 12 + 12) / 10 = 29/10 = 2.9。

## 例 3：二分查找插入元素（保持有序）

### C++ 代码实现

```cpp

#include <vector>
using namespace std;

// 在有序向量v（升序）中插入x，保持有序
void binaryInsert(vector<int>& v, int x) {
    int left = 0, right = v.size() - 1;
    // 查找插入位置：第一个大于x的元素索引
    while (left <= right) {
        int mid = left + (right - left) / 2;
        if (v[mid] < x) {
            left = mid + 1;
        } else {
            right = mid - 1;
        }
    }
    // 在left位置插入x
    v.insert(v.begin() + left, x);
}
```

## 例 4：二叉排序树操作

### 1. 构造二叉排序树（数据集合 d={1,12,5,8,3,10,7,13,9}）

按顺序插入元素，树结构如下：

- 根节点：1

- 12>1 → 右子树；5>1 且 < 12 → 12 的左子树；

- 8>5 → 5 的右子树；3<5 → 5 的左子树；

- 10>8 → 8 的右子树；7<8 且> 5 → 8 的左子树；

- 13>12 → 12 的右子树；9<10 且> 8 → 10 的左子树。

最终树结构（根→左 / 右）：
1 → 右 (12)
12 → 左 (5)、右 (13)
5 → 左 (3)、右 (8)
8 → 左 (7)、右 (10)
10 → 左 (9)

### 2. 得到有序序列的方式

对二叉排序树进行**中序遍历**，即可得到升序序列：1,3,5,7,8,9,10,12,13。

### 3. 删除 “12” 后的树结构

12 是根节点的右子节点，且有两个子节点（左 5，右 13）：

- 找 12 的右子树最小节点（即 13，叶子节点）；

- 用 13 替换 12 的值；

- 删除原 13 节点。

删除后结构：
1 → 右 (13)
13 → 左 (5)（原 12 的左子树）
5 → 左 (3)、右 (8)（后续结构不变）

## 例 5：二叉排序树中任意两节点的最近公共祖先（LCA）

### C++ 代码实现

```cpp

#include <iostream>
using namespace std;

struct BSTNode { // 复用之前的BSTNode结构
    int val;
    BSTNode* left;
    BSTNode* right;
    BSTNode(int x) : val(x), left(nullptr), right(nullptr) {}
};

// 查找p和q的最近公共祖先
BSTNode* findLCA(BSTNode* root, BSTNode* p, BSTNode* q) {
    if (!root || root == p || root == q) return root;
    // 两节点都在左子树
    if (p->val < root->val && q->val < root->val) {
        return findLCA(root->left, p, q);
    }
    // 两节点都在右子树
    if (p->val > root->val && q->val > root->val) {
        return findLCA(root->right, p, q);
    }
    // 两节点分别在左右子树，当前节点即为LCA
    return root;
}
```

## 例 6：AVL 树构造与节点数计算

### 1. 插入序列 {4,5,7,2,1,3,6} 构造 AVL 树

按顺序插入并执行平衡化旋转：

1. 插入 4 → 根 (4)（平衡）。

2. 插入 5 → 4 的右子树（平衡因子 - 1，平衡）。

3. 插入 7 → 5 的右子树，4 的平衡因子 - 2（RR 型），左单旋后根为 5（5→4, 5→7）（平衡）。

4. 插入 2 → 4 的左子树（平衡）。

5. 插入 1 → 2 的左子树，4 的平衡因子 2（LL 型），右单旋后 4 的父节点变为 2（5→2, 2→4, 5→7；2→1）（平衡）。

6. 插入 3 → 4 的左子树，2 的平衡因子 - 1，4 的平衡因子 1（LR 型）：先左旋 4 的左子树（无变化），再右旋 2，最终根为 4（4→2, 4→5；2→1, 2→3；5→7）（平衡）。

7. 插入 6 → 7 的左子树，5 的平衡因子 - 1，7 的平衡因子 1（RL 型）：先右旋 7，再左旋 5，最终 5 的右子树变为 6（4→2, 4→6；2→1, 2→3；6→5, 6→7）（平衡）。

最终 AVL 树的根为 4，平衡因子均满足≤1。

### 2. 高度为 5 的 AVL 树节点数

- 最少节点数：按递推公式 S (h) = S (h-1) + S (h-2) + 1（S (0)=0, S (1)=1）：
S (2)=S (1)+S (0)+1=2；S (3)=S (2)+S (1)+1=4；S (4)=S (3)+S (2)+1=7；S (5)=S (4)+S (3)+1=12。

- 最多节点数：满二叉树，2⁵ - 1 = 31。

需要我帮你把某个习题的代码补充完整，或者针对某个知识点做更细致的代码演示吗？
> （注：文档部分内容可能由 AI 生成）