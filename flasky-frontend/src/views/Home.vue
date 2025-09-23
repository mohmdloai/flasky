
<template>
  <div class="text-center">
    <h1 class="text-4xl font-bold text-gray-900 mb-8">
      Welcome to Flasky Inventory
    </h1>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
      <a-card
        hoverable
        class="cursor-pointer"
        @click="$router.push('/products')"
      >
        <template #cover>
          <div class="h-32 bg-blue-100 flex items-center justify-center">
            <ShopOutlined class="text-4xl text-blue-600" />
          </div>
        </template>
        <a-card-meta
          title="Manage Products"
          description="Add, view, and manage your product inventory"
        />
      </a-card>

      <a-card hoverable class="cursor-pointer" @click="$router.push('/orders')">
        <template #cover>
          <div class="h-32 bg-green-100 flex items-center justify-center">
            <ShoppingCartOutlined class="text-4xl text-green-600" />
          </div>
        </template>
        <a-card-meta
          title="Manage Orders"
          description="Create orders, process payments, and track shipments"
        />
      </a-card>
    </div>
  </div>
</template>

<script setup>
import { ShopOutlined, ShoppingCartOutlined } from "@ant-design/icons-vue";
</script>
