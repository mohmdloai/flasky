<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold text-gray-900">Products</h1>
      <a-button type="primary" @click="showAddModal = true">
        <PlusOutlined />
        Add Product
      </a-button>
    </div>

    <a-table
      :columns="columns"
      :data-source="products"
      :loading="loading"
      :pagination="pagination"
      @change="handleTableChange"
      row-key="id"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'price'">
          ${{ record.price.toFixed(2) }}
        </template>
        <template v-else-if="column.key === 'stock'">
          <a-tag
            :color="
              record.stock > 5 ? 'green' : record.stock > 0 ? 'orange' : 'red'
            "
          >
            {{ record.stock }}
          </a-tag>
        </template>
      </template>
    </a-table>

    <!-- Add Product Modal -->
    <a-modal
      v-model:open="showAddModal"
      title="Add New Product"
      @ok="addProduct"
      :confirm-loading="addingProduct"
    >
      <a-form :model="newProduct" layout="vertical">
        <a-form-item label="Name" required>
          <a-input v-model:value="newProduct.name" placeholder="Product name" />
        </a-form-item>
        <a-form-item label="Price" required>
          <a-input-number
            v-model:value="newProduct.price"
            :min="0"
            :precision="2"
            style="width: 100%"
            placeholder="0.00"
          />
        </a-form-item>
        <a-form-item label="Stock" required>
          <a-input-number
            v-model:value="newProduct.stock"
            :min="0"
            style="width: 100%"
            placeholder="0"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { message } from "ant-design-vue";
import { PlusOutlined } from "@ant-design/icons-vue";
import { productsApi } from "../services/api";

const products = ref([]);
const loading = ref(false);
const showAddModal = ref(false);
const addingProduct = ref(false);

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total) => `Total ${total} products`,
});

const newProduct = ref({
  name: "",
  price: null,
  stock: null,
});

const columns = [
  {
    title: "ID",
    dataIndex: "id",
    key: "id",
    width: 80,
  },
  {
    title: "Name",
    dataIndex: "name",
    key: "name",
  },
  {
    title: "Price",
    dataIndex: "price",
    key: "price",
  },
  {
    title: "Stock",
    dataIndex: "stock",
    key: "stock",
  },
];

const fetchProducts = async (page = 1, pageSize = 10) => {
  loading.value = true;
  try {
    const response = await productsApi.getAll({
      page,
      page_size: pageSize,
    });

    products.value = response.data || [];

    // Update pagination from meta
    if (response.meta?.pagination) {
      const paginationMeta = response.meta.pagination;
      pagination.current = paginationMeta.current_page;
      pagination.pageSize = paginationMeta.page_size;
      pagination.total = paginationMeta.total_items;
    }
  } catch (error) {
    message.error(error.message || "Failed to fetch products");
  } finally {
    loading.value = false;
  }
};

const handleTableChange = (pag) => {
  fetchProducts(pag.current, pag.pageSize);
};

const addProduct = async () => {
  if (
    !newProduct.value.name ||
    newProduct.value.price === null ||
    newProduct.value.stock === null
  ) {
    message.warning("Please fill in all fields");
    return;
  }

  addingProduct.value = true;
  try {
    await productsApi.create(newProduct.value);
    message.success("Product added successfully");
    showAddModal.value = false;
    newProduct.value = { name: "", price: null, stock: null };
    fetchProducts(pagination.current, pagination.pageSize);
  } catch (error) {
    message.error(error.message || "Failed to add product");
  } finally {
    addingProduct.value = false;
  }
};

onMounted(() => fetchProducts());
</script>
