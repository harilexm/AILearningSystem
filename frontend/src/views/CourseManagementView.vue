<template>
  <div class="course-mgmt-container">
    <h1>Course Management</h1>
    <p>Create and structure your educational courses here.</p>

    <!-- Create Course Form -->
    <div class="card">
      <h2>Create a New Course</h2>
      <form @submit.prevent="handleCreateCourse">
        <div class="form-group">
          <label for="courseTitle">Course Title</label>
          <input id="courseTitle" v-model="newCourse.title" type="text" placeholder="e.g., Introduction to Algebra" required />
        </div>
        <div class="form-group">
          <label for="courseDesc">Course Description</label>
          <textarea id="courseDesc" v-model="newCourse.description" placeholder="A brief summary of the course..."></textarea>
        </div>
        <button type="submit" class="btn">Create Course</button>
      </form>
    </div>

    <!-- Display existing courses -->
    <div class="card">
        <h2>Existing Courses</h2>
        <div v-if="isLoading">Loading courses...</div>
        <ul v-else-if="courses.length > 0">
            <li v-for="course in courses" :key="course.id">{{ course.title }}</li>
        </ul>
        <p v-else>No courses created yet.</p>
    </div>

    <p v-if="message" class="message" :class="isError ? 'error' : 'success'">{{ message }}</p>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import axios from 'axios';

const authStore = useAuthStore();
const courses = ref([]);
const isLoading = ref(true);
const message = ref('');
const isError = ref(false);

const newCourse = ref({
  title: '',
  description: ''
});

const apiClient = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: {
    Authorization: `Bearer ${authStore.token}`
  }
});

const fetchCourses = async () => {
    isLoading.value = true;
    try {
        const response = await apiClient.get('/courses');
        courses.value = response.data;
    } catch (err) {
        message.value = 'Failed to load courses.';
        isError.value = true;
    } finally {
        isLoading.value = false;
    }
};

const handleCreateCourse = async () => {
  message.value = '';
  isError.value = false;
  try {
    const response = await apiClient.post('/courses', newCourse.value);
    message.value = response.data.message;
    // Reset form and refresh list
    newCourse.value.title = '';
    newCourse.value.description = '';
    await fetchCourses();
  } catch (err) {
    message.value = err.response?.data?.error || 'Failed to create course.';
    isError.value = true;
  }
};

onMounted(fetchCourses);
</script>

<style scoped>
.course-mgmt-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 1rem;
}
.card {
  background: #fff;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
}
.form-group {
  margin-bottom: 1.5rem;
}
label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}
input, textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
}
textarea {
    min-height: 100px;
}
.btn {
  background-color: #007bff;
  color: white;
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.message {
  padding: 1rem;
  border-radius: 4px;
  text-align: center;
}
.success { background-color: #d4edda; color: #155724; }
.error { background-color: #f8d7da; color: #721c24; }
</style>