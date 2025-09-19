
<template>
  <div v-if="order">
    <div class="flex items-center justify-between mb-6">
      <div>
        <a-button @click="$router.go(-1)" class="mb-4">
          <ArrowLeftOutlined />
          Back
        </a-button>
        <h1 class="text-3xl font-bold text-gray-900">Order #{{ order.id }}</h1>
      </div>

      <div class="text-right">
        <div class="mb-2">
          <a-tag :color="getStatusColor(order.payment_status)" class="text-sm">
            Payment: {{ order.payment_status.toUpperCase() }}
          </a-tag>
        </div>
        <div>
          <a-tag :color="getStatusColor(order.shipping_status)" class="text-sm">
            Shipping:
            {{ order.shipping_status.replace("_", " ").toUpperCase() }}
          </a-tag>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Order Information -->
      <div class="lg:col-span-2">
        <a-card title="Order Items" class="mb-6">
          <a-table
            :columns="itemColumns"
            :data-source="order.items"
            :pagination="false"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'price'">
                ${{ record.product?.price?.toFixed(2) }}
              </template>
              <template v-else-if="column.key === 'total'">
                ${{ (record.quantity * record.product?.price)?.toFixed(2) }}
              </template>
            </template>
          </a-table>
        </a-card>

        <!-- Add Items Section (if order is unpaid) -->
        <a-card
          v-if="order.payment_status === 'pending'"
          title="Add More Items"
        >
          <a-form layout="inline" @submit.prevent="addItemToOrder">
            <a-form-item>
              <a-select
                v-model:value="newItem.product_id"
                placeholder="Select Product"
                style="width: 200px"
              >
                <a-select-option
                  v-for="product in availableProducts"
                  :key="product.id"
                  :value="product.id"
                >
                  {{ product.name }} (${{ product.price }})
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item>
              <a-input-number
                v-model:value="newItem.quantity"
                :min="1"
                placeholder="Quantity"
                style="width: 100px"
              />
            </a-form-item>

            <a-form-item>
              <a-button
                type="primary"
                @click="addItemToOrder"
                :loading="addingItem"
              >
                Add Item
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </div>

      <!-- Order Summary -->
      <div>
        <a-card title="Order Summary">
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700"
                >Customer</label
              >
              <p class="text-lg">{{ order.name }}</p>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700"
                >Email</label
              >
              <p class="text-lg">{{ order.email }}</p>
            </div>

            <div v-if="order.payment_reference">
              <label class="block text-sm font-medium text-gray-700"
                >Payment Reference</label
              >
              <p class="text-lg font-mono">{{ order.payment_reference }}</p>
            </div>

            <a-divider />

            <div>
              <label class="block text-sm font-medium text-gray-700"
                >Total Amount</label
              >
              <p class="text-2xl font-bold text-green-600">
                ${{ order.total_amount?.toFixed(2) }}
              </p>
            </div>

            <a-button
              v-if="order.payment_status === 'pending'"
              type="primary"
              size="large"
              block
              @click="payOrder"
              :loading="processing"
            >
              Process Payment
            </a-button>
          </div>
        </a-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { message } from "ant-design-vue";
import { ArrowLeftOutlined } from "@ant-design/icons-vue";
import { ordersApi, productsApi } from "../services/api";

const props = defineProps(["id"]);
const router = useRouter();

const order = ref(null);
const availableProducts = ref([]);
const processing = ref(false);
const addingItem = ref(false);

const newItem = ref({
  product_id: null,
  quantity: 1,
});

const itemColumns = [
  {
    title: "Product",
    dataIndex: ["product", "name"],
    key: "product",
  },
  {
    title: "Price",
    key: "price",
  },
  {
    title: "Quantity",
    dataIndex: "quantity",
    key: "quantity",
  },
  {
    title: "Total",
    key: "total",
  },
];

const getStatusColor = (status) => {
  const colors = {
    pending: "orange",
    paid: "green",
    in_progress: "blue",
    delivered: "green",
  };
  return colors[status] || "default";
};

const fetchOrder = async () => {
  try {
    const response = await ordersApi.getById(props.id);
    order.value = response.data;
  } catch (error) {
    message.error("Failed to fetch order details");
    router.push("/orders");
  }
};

const fetchProducts = async () => {
  try {
    const response = await productsApi.getAll();
    availableProducts.value = response.data;
  } catch (error) {
    message.error("Failed to fetch products");
  }
};

const addItemToOrder = async () => {
  if (!newItem.value.product_id || !newItem.value.quantity) {
    message.warning("Please select a product and quantity");
    return;
  }

  addingItem.value = true;
  try {
    await ordersApi.addItem(props.id, newItem.value);
    message.success("Item added successfully");
    newItem.value = { product_id: null, quantity: 1 };
    fetchOrder(); // Refresh order data
  } catch (error) {
    message.error(error.response?.data?.error || "Failed to add item");
  } finally {
    addingItem.value = false;
  }
};

const payOrder = async () => {
  processing.value = true;
  try {
    const response = await ordersApi.pay(props.id);
    message.success("Payment successful!");
    order.value = response.data.order;
  } catch (error) {
    message.error(error.response?.data?.error || "Payment failed");
  } finally {
    processing.value = false;
  }
};

onMounted(() => {
  fetchOrder();
  fetchProducts();
});
</script>
