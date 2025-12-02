"""Simple test class for Milvus client."""
from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.utils.milvus_client import MilvusClient
from app.logger import get_logger

logger = get_logger(__name__)


class MilvusClientTest:
    """Simple test class for Milvus client."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        user: str = "",
        password: str = "",
    ):
        """
        Initialize test class.

        Args:
            host: Milvus server host
            port: Milvus server port
            user: Username for authentication
            password: Password for authentication
        """
        self.client = MilvusClient(host=host, port=port, user=user, password=password)
        self.test_collection_name = "test_collection"

    def test_connection(self) -> bool:
        """
        Test connection to Milvus.

        Returns:
            True if connection successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("🧪 测试 1: 连接 Milvus")
        print("=" * 60)

        try:
            result = self.client.connect()
            if result:
                print("✅ 连接成功")
                # Test is_connected
                if self.client.is_connected():
                    print("✅ 连接状态检查通过")
                else:
                    print("❌ 连接状态检查失败")
                    return False
                return True
            else:
                print("❌ 连接失败")
                return False
        except Exception as e:
            print(f"❌ 连接错误: {e}")
            logger.error(f"Connection test failed: {e}", exc_info=True)
            return False

    def test_create_collection(self) -> bool:
        """
        Test creating a collection.

        Returns:
            True if collection created successfully, False otherwise
        """
        print("\n" + "=" * 60)
        print("🧪 测试 2: 创建集合")
        print("=" * 60)

        try:
            # Clean up if collection exists
            if self.client.collection_exists(self.test_collection_name):
                print(f"⚠️  集合 '{self.test_collection_name}' 已存在，先删除...")
                self.client.drop_collection(self.test_collection_name)

            # Create collection with embedding field
            result = self.client.create_collection_with_embedding(
                collection_name=self.test_collection_name,
                embedding_dim=128,  # Small dimension for testing
                text_field_name="text",
                embedding_field_name="embedding",
                description="Test collection for Milvus client",
            )

            if result:
                print(f"✅ 集合 '{self.test_collection_name}' 创建成功")

                # Verify collection exists
                if self.client.collection_exists(self.test_collection_name):
                    print("✅ 集合存在验证通过")
                else:
                    print("❌ 集合存在验证失败")
                    return False

                # Get collection info
                info = self.client.get_collection_info(self.test_collection_name)
                if info:
                    print(f"✅ 集合信息获取成功: {info['num_entities']} 条数据")
                    print(f"   字段数: {len(info['schema']['fields'])}")
                else:
                    print("⚠️  无法获取集合信息")

                return True
            else:
                print("❌ 集合创建失败")
                return False
        except Exception as e:
            print(f"❌ 创建集合错误: {e}")
            logger.error(f"Create collection test failed: {e}", exc_info=True)
            return False

    def test_create_index(self) -> bool:
        """
        Test creating an index.

        Returns:
            True if index created successfully, False otherwise
        """
        print("\n" + "=" * 60)
        print("🧪 测试 3: 创建索引")
        print("=" * 60)

        try:
            result = self.client.create_index(
                collection_name=self.test_collection_name,
                field_name="embedding",
                index_type="IVF_FLAT",
                metric_type="L2",
                params={"nlist": 128},  # Small nlist for testing
            )

            if result:
                print("✅ 索引创建成功")
                return True
            else:
                print("❌ 索引创建失败")
                return False
        except Exception as e:
            print(f"❌ 创建索引错误: {e}")
            logger.error(f"Create index test failed: {e}", exc_info=True)
            return False

    def test_insert_data(self) -> bool:
        """
        Test inserting data.

        Returns:
            True if data inserted successfully, False otherwise
        """
        print("\n" + "=" * 60)
        print("🧪 测试 4: 插入数据")
        print("=" * 60)

        try:
            # Generate test data
            test_texts = [
                "这是第一条测试文本",
                "这是第二条测试文本",
                "这是第三条测试文本",
            ]

            # Generate simple test embeddings (128 dimensions)
            import random

            random.seed(42)  # For reproducibility
            test_embeddings = [
                [random.random() for _ in range(128)] for _ in range(len(test_texts))
            ]

            # Prepare data - when using field_names, data should be organized by field (column-major)
            # Format: [[field1_values], [field2_values], ...]
            data = [test_texts, test_embeddings]
            field_names = ["text", "embedding"]

            # Insert data
            result = self.client.insert(
                collection_name=self.test_collection_name,
                data=data,
                field_names=field_names,
            )

            if result:
                print(f"✅ 成功插入 {len(data)} 条数据")
                print(f"   插入的 ID: {result[:3]}...")  # Show first 3 IDs

                # Verify collection stats
                stats = self.client.get_collection_stats(self.test_collection_name)
                if stats:
                    print(f"✅ 集合统计: {stats['num_entities']} 条数据")
                    if stats["num_entities"] == len(data):
                        print("✅ 数据数量验证通过")
                    else:
                        print(
                            f"⚠️  数据数量不匹配: 期望 {len(data)}, 实际 {stats['num_entities']}"
                        )
                return True
            else:
                print("❌ 数据插入失败")
                return False
        except Exception as e:
            print(f"❌ 插入数据错误: {e}")
            logger.error(f"Insert data test failed: {e}", exc_info=True)
            return False

    def test_search(self) -> bool:
        """
        Test vector search.

        Returns:
            True if search successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("🧪 测试 5: 向量搜索")
        print("=" * 60)

        try:
            # Load collection
            if not self.client.load_collection(self.test_collection_name):
                print("❌ 加载集合失败")
                return False

            # Generate a query vector
            import random

            random.seed(42)
            query_vector = [[random.random() for _ in range(128)]]

            # Search
            results = self.client.search(
                collection_name=self.test_collection_name,
                query_vectors=query_vector,
                anns_field="embedding",
                limit=3,
                output_fields=["text"],
            )

            if results:
                print(f"✅ 搜索成功，返回 {len(results)} 组结果")
                for i, result_group in enumerate(results):
                    print(f"\n   结果组 {i + 1}:")
                    for j, hit in enumerate(result_group):
                        print(
                            f"     排名 {j + 1}: ID={hit.id}, 距离={hit.distance:.4f}, 文本={hit.entity.get('text', 'N/A')}"
                        )
                return True
            else:
                print("❌ 搜索失败")
                return False
        except Exception as e:
            print(f"❌ 搜索错误: {e}")
            logger.error(f"Search test failed: {e}", exc_info=True)
            return False

    def test_query(self) -> bool:
        """
        Test query with expression.

        Returns:
            True if query successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("🧪 测试 6: 表达式查询")
        print("=" * 60)

        try:
            # Query all entities
            results = self.client.query(
                collection_name=self.test_collection_name,
                expr="text != ''",  # Query all non-empty texts
                output_fields=["text"],
                limit=10,
            )

            if results is not None:
                print(f"✅ 查询成功，返回 {len(results)} 条结果")
                for i, result in enumerate(results[:3]):  # Show first 3
                    print(f"   结果 {i + 1}: {result.get('text', 'N/A')}")
                return True
            else:
                print("❌ 查询失败")
                return False
        except Exception as e:
            print(f"❌ 查询错误: {e}")
            logger.error(f"Query test failed: {e}", exc_info=True)
            return False

    def test_delete(self) -> bool:
        """
        Test deleting data.

        Returns:
            True if deletion successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("🧪 测试 7: 删除数据")
        print("=" * 60)

        try:
            # Get current count
            stats_before = self.client.get_collection_stats(self.test_collection_name)
            count_before = stats_before["num_entities"] if stats_before else 0
            print(f"   删除前: {count_before} 条数据")

            # Delete one entity (if we have IDs, we can delete by ID)
            # For this test, we'll delete by text content
            result = self.client.delete(
                collection_name=self.test_collection_name,
                expr='text == "这是第一条测试文本"',
            )

            if result:
                # Get count after deletion
                stats_after = self.client.get_collection_stats(self.test_collection_name)
                count_after = stats_after["num_entities"] if stats_after else 0
                print(f"   删除后: {count_after} 条数据")

                if count_after < count_before:
                    print("✅ 删除成功")
                    return True
                else:
                    print("⚠️  数据数量未减少")
                    return False
            else:
                print("❌ 删除失败")
                return False
        except Exception as e:
            print(f"❌ 删除错误: {e}")
            logger.error(f"Delete test failed: {e}", exc_info=True)
            return False

    def test_cleanup(self) -> bool:
        """
        Test cleanup (drop collection).

        Returns:
            True if cleanup successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("🧪 测试 8: 清理（删除集合）")
        print("=" * 60)

        try:
            # Release collection first
            self.client.release_collection(self.test_collection_name)

            # Drop collection
            result = self.client.drop_collection(self.test_collection_name)

            if result:
                # Verify collection is deleted
                if not self.client.collection_exists(self.test_collection_name):
                    print("✅ 集合删除成功")
                    return True
                else:
                    print("❌ 集合仍然存在")
                    return False
            else:
                print("❌ 集合删除失败")
                return False
        except Exception as e:
            print(f"❌ 清理错误: {e}")
            logger.error(f"Cleanup test failed: {e}", exc_info=True)
            return False

    def test_disconnect(self) -> bool:
        """
        Test disconnection.

        Returns:
            True if disconnection successful, False otherwise
        """
        print("\n" + "=" * 60)
        print("🧪 测试 9: 断开连接")
        print("=" * 60)

        try:
            self.client.disconnect()
            print("✅ 断开连接成功")
            return True
        except Exception as e:
            print(f"❌ 断开连接错误: {e}")
            logger.error(f"Disconnect test failed: {e}", exc_info=True)
            return False

    def run_all_tests(self) -> dict[str, bool]:
        """
        Run all tests.

        Returns:
            Dictionary with test names and results
        """
        print("\n" + "=" * 60)
        print("🚀 开始 Milvus 客户端测试")
        print("=" * 60)

        results = {}

        # Test 1: Connection
        results["连接"] = self.test_connection()
        if not results["连接"]:
            print("\n❌ 连接失败，跳过后续测试")
            return results

        # Test 2: Create collection
        results["创建集合"] = self.test_create_collection()
        if not results["创建集合"]:
            print("\n❌ 创建集合失败，跳过后续测试")
            self.client.disconnect()
            return results

        # Test 3: Create index
        results["创建索引"] = self.test_create_index()

        # Test 4: Insert data
        results["插入数据"] = self.test_insert_data()

        # Test 5: Search
        results["向量搜索"] = self.test_search()

        # Test 6: Query
        results["表达式查询"] = self.test_query()

        # Test 7: Delete
        results["删除数据"] = self.test_delete()

        # Test 8: Cleanup
        results["清理"] = self.test_cleanup()

        # Test 9: Disconnect
        results["断开连接"] = self.test_disconnect()

        # Summary
        print("\n" + "=" * 60)
        print("📊 测试结果汇总")
        print("=" * 60)
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        for test_name, result in results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"  {test_name}: {status}")

        print(f"\n总计: {passed}/{total} 测试通过")
        if passed == total:
            print("🎉 所有测试通过！")
        else:
            print("⚠️  部分测试失败")

        return results


def main():
    """Main function to run tests."""
    import os

    # Get connection parameters from environment or use defaults
    host = os.getenv("MILVUS_HOST", "localhost")
    port = int(os.getenv("MILVUS_PORT", "19530"))
    user = os.getenv("MILVUS_USER", "")
    password = os.getenv("MILVUS_PASSWORD", "")

    print(f"\n配置信息:")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  User: {user if user else '(未设置)'}")
    print(f"  Password: {'*' * len(password) if password else '(未设置)'}")

    # Create test instance
    test = MilvusClientTest(host=host, port=port, user=user, password=password)

    # Run all tests
    try:
        results = test.run_all_tests()
        # Exit with appropriate code
        exit_code = 0 if all(results.values()) else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 测试中断")
        test.client.disconnect()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        print(f"\n❌ 测试执行失败: {e}")
        test.client.disconnect()
        sys.exit(1)


if __name__ == "__main__":
    main()

