<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold text-gray-900">Orders</h1>
      <a-button type="primary" @click="showCreateModal = true">
        <PlusOutlined />
        Create Order
      </a-button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <a-card
        v-for="order in orders"
        :key="order.id"
        :title="`Order #${order.id}`"
        class="cursor-pointer hover:shadow-lg transition-shadow"
        @click="viewOrder(order.id)"
      >
        <p class="mb-2"><strong>Customer:</strong> {{ order.name }}</p>
        <p class="mb-2"><strong>Email:</strong> {{ order.email }}</p>
        <p class="mb-2">
          <strong>Total:</strong> ${{ order.total_amount?.toFixed(2) }}
        </p>

        <div class="flex justify-between items-center mt-4">
          <div>
            <a-tag :color="getStatusColor(order.payment_status)">
              {{ order.payment_status.toUpperCase() }}
            </a-tag>
            <a-tag :color="getStatusColor(order.shipping_status)">
              {{ order.shipping_status.replace("_", " ").toUpperCase() }}
            </a-tag>
          </div>

          <a-button
            v-if="order.payment_status === 'pending'"
            type="primary"
            size="small"
            @click.stop="payOrder(order.id)"
          >
            Pay Now
          </a-button>
        </div>
      </a-card>
    </div>

    <!-- Create Order Modal -->
    <a-modal
      v-model:open="showCreateModal"
      title="Create New Order"
      @ok="createOrder"
      :confirm-loading="creatingOrder"
      width="800px"
    >
      <a-form :model="newOrder" layout="vertical">
        <div class="grid grid-cols-2 gap-4">
          <a-form-item label="Customer Name" required>
            <a-input
              v-model:value="newOrder.name"
              placeholder="Enter customer name"
            />
          </a-form-item>
          <a-form-item label="Email" required>
            <a-input v-model:value="newOrder.email" placeholder="Enter email" />
          </a-form-item>
        </div>

        <a-form-item label="Order Items" required>
          <div class="space-y-4">
            <div
              v-for="(item, index) in newOrder.items"
              :key="index"
              class="flex items-center space-x-4 p-4 border rounded-lg"
            >
              <a-select
                v-model:value="item.product_id"
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

              <a-input-number
                v-model:value="item.quantity"
                :min="1"
                placeholder="Qty"
                style="width: 100px"
              />

              <a-button
                type="text"
                danger
                @click="removeItem(index)"
                v-if="newOrder.items.length > 1"
              >
                <DeleteOutlined />
              </a-button>
            </div>

            <a-button type="dashed" @click="addItem" block>
              <PlusOutlined />
              Add Item
            </a-button>
          </div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { message } from "ant-design-vue";
import { PlusOutlined, DeleteOutlined } from "@ant-design/icons-vue";
import { ordersApi, productsApi } from "../services/api";

const router = useRouter();
const orders = ref([]);
const availableProducts = ref([]);
const showCreateModal = ref(false);
const creatingOrder = ref(false);

const newOrder = ref({
  name: "",
  email: "",
  items: [{ product_id: null, quantity: 1 }],
});

const fetchOrders = async () => {
  try {
    const response = await ordersApi.getAll();
    orders.value = response.data;
  } catch (error) {
    message.error("Failed to fetch orders");
    console.error("Orders fetch error:", error);
  }
};

const getStatusColor = (status) => {
  const colors = {
    pending: "orange",
    paid: "green",
    in_progress: "blue",
    delivered: "green",
  };
  return colors[status] || "default";
};

const addItem = () => {
  newOrder.value.items.push({ product_id: null, quantity: 1 });
};

const removeItem = (index) => {
  newOrder.value.items.splice(index, 1);
};

const fetchProducts = async () => {
  try {
    const response = await productsApi.getAll();
    availableProducts.value = response.data;
  } catch (error) {
    message.error("Failed to fetch products");
  }
};

const createOrder = async () => {
  if (
    !newOrder.value.name ||
    !newOrder.value.email ||
    !newOrder.value.items.length
  ) {
    message.warning("Please fill in all required fields");
    return;
  }

  // Validate items
  for (const item of newOrder.value.items) {
    if (!item.product_id || !item.quantity) {
      message.warning("Please complete all order items");
      return;
    }
  }

  creatingOrder.value = true;
  try {
    const response = await ordersApi.create(newOrder.value);
    message.success("Order created successfully");
    orders.value.unshift(response.data);
    showCreateModal.value = false;
    newOrder.value = {
      name: "",
      email: "",
      items: [{ product_id: null, quantity: 1 }],
    };
  } catch (error) {
    message.error(error.response?.data?.error || "Failed to create order");
  } finally {
    creatingOrder.value = false;
  }
};

const payOrder = async (orderId) => {
  try {
    const response = await ordersApi.pay(orderId);
    message.success("Payment successful!");

    // Update the order in the list
    const orderIndex = orders.value.findIndex((o) => o.id === orderId);
    if (orderIndex !== -1) {
      orders.value[orderIndex] = response.data.order;
    }
  } catch (error) {
    message.error(error.response?.data?.error || "Payment failed");
  }
};

const viewOrder = (orderId) => {
  router.push(`/orders/${orderId}`);
};

onMounted(() => {
  fetchProducts();
  fetchOrders(); // Add this line to fetch real orders
});
</script>
