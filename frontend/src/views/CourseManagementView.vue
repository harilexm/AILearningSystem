<template>
  <div class="course-mgmt-container">
    <h1>Course Management</h1>
    
    <div class="main-grid">
      <!-- Left Column: Course List and Creation -->
      <div class="course-list-panel">
        <div class="card">
          <h2>Create a New Course</h2>
          <form @submit.prevent="handleCreateCourse">
            <div class="form-group">
              <label for="courseTitle">Course Title</label>
              <input id="courseTitle" v-model="newCourse.title" type="text" required />
            </div>
            <div class="form-group">
              <label for="courseDesc">Course Description</label>
              <textarea id="courseDesc" v-model="newCourse.description"></textarea>
            </div>
            <button type="submit" class="btn">Create Course</button>
          </form>
        </div>

        <div class="card">
          <h2>Existing Courses</h2>
          <div v-if="isLoadingCourses">Loading...</div>
          <ul v-else-if="courses.length > 0" class="course-list">
            <li v-for="course in courses" :key="course.id" @click="selectCourse(course.id)" :class="{ selected: selectedCourse?.id === course.id }">
              {{ course.title }}
            </li>
          </ul>
          <p v-else>No courses created yet.</p>
        </div>
      </div>

      <!-- Right Column: Course Builder -->
      <div class="course-builder-panel">
        <div v-if="!selectedCourse" class="card placeholder">
          <p>Select a course on the left to start building.</p>
        </div>
        
        <div v-else>
          <h2>Building: {{ selectedCourse.title }}</h2>
          <RouterLink 
            :to="{ name: 'course-progress', params: { courseId: selectedCourse.id } }" 
            class="btn btn-secondary"
          >
            View Student Progress
          </RouterLink>
          
          <!-- Modules Section -->
          <div v-for="module in selectedCourse.modules" :key="module.id" class="card module-card">
            <h3>Module {{ module.order }}: {{ module.title }}</h3>
            <!-- Existing Content -->
            <ul class="content-list">
              <li v-for="content in module.learning_contents" :key="content.id" class="content-item">
                <span>{{ content.order }}. {{ content.title }} ({{ content.type }})</span>
              </li>
              <li v-if="!module.learning_contents.length" class="content-item-empty">No content yet.</li>
            </ul>
            <!-- Add New Content Form -->
            <form @submit.prevent="handleAddContent(module.id)" class="add-content-form">
              <h4>Add New Content</h4>
              <input v-model="newContent[module.id].title" type="text" placeholder="Content Title" required/>
              <select v-model="newContent[module.id].type">
                <option value="video">Video</option>
                <option value="article">Article</option>
              </select>
              <input v-model="newContent[module.id].url" type="text" placeholder="Content URL (for videos)" />
              <button type="submit" class="btn-small">Add Content</button>
            </form>
          </div>

          <!-- Add New Module Form -->
          <div class="card">
            <h2>Add New Module</h2>
            <form @submit.prevent="handleAddModule">
              <input v-model="newModule.title" type="text" placeholder="Module Title" required />
              <button type="submit" class="btn">Add Module</button>
            </form>
          </div>
        </div>
      </div>
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
const selectedCourse = ref(null);
const isLoadingCourses = ref(true);
const message = ref('');
const isError = ref(false);

const newCourse = ref({ title: '', description: '' });
const newModule = ref({ title: '', description: '' });
const newContent = ref({}); // Use an object keyed by module ID

const apiClient = axios.create({
  baseURL: 'http://localhost:5000/api',
  headers: { Authorization: `Bearer ${authStore.token}` }
});

const fetchCourses = async () => {
  isLoadingCourses.value = true;
  try {
    const response = await apiClient.get('/courses');
    courses.value = response.data;
  } catch (err) { handleApiError(err, 'Failed to load courses.'); }
  finally { isLoadingCourses.value = false; }
};

const selectCourse = async (courseId) => {
  try {
    const response = await apiClient.get(`/courses/${courseId}`);
    selectedCourse.value = response.data;
    // Initialize newContent objects for each module
    selectedCourse.value.modules.forEach(module => {
      newContent.value[module.id] = { title: '', type: 'video', url: '', body: '' };
    });
  } catch (err) { handleApiError(err, 'Failed to load course details.'); }
};

const handleCreateCourse = async () => {
  try {
    await apiClient.post('/courses', newCourse.value);
    showApiMessage('Course created successfully.');
    newCourse.value = { title: '', description: '' };
    await fetchCourses();
  } catch (err) { handleApiError(err, 'Failed to create course.'); }
};

const handleAddModule = async () => {
  const nextOrder = (selectedCourse.value.modules.length || 0) + 1;
  const payload = { ...newModule.value, order: nextOrder };
  try {
    await apiClient.post(`/courses/${selectedCourse.value.id}/modules`, payload);
    showApiMessage('Module added successfully.');
    newModule.value.title = '';
    await selectCourse(selectedCourse.value.id); // Refresh details
  } catch (err) { handleApiError(err, 'Failed to add module.'); }
};

const handleAddContent = async (moduleId) => {
  const module = selectedCourse.value.modules.find(m => m.id === moduleId);
  const nextOrder = (module.learning_contents.length || 0) + 1;
  const payload = { ...newContent.value[moduleId], order: nextOrder };
  try {
    await apiClient.post(`/modules/${moduleId}/content`, payload);
    showApiMessage('Content added successfully.');
    newContent.value[moduleId] = { title: '', type: 'video', url: '', body: '' };
    await selectCourse(selectedCourse.value.id); // Refresh details
  } catch (err) { handleApiError(err, 'Failed to add content.'); }
};

const showApiMessage = (msg, error = false) => {
  message.value = msg;
  isError.value = error;
  setTimeout(() => message.value = '', 4000);
};
const handleApiError = (err, defaultMsg) => {
  const errorMsg = err.response?.data?.error || defaultMsg;
  showApiMessage(errorMsg, true);
};

onMounted(fetchCourses);
</script>

<style scoped>
.main-grid { display: grid; grid-template-columns: 350px 1fr; gap: 2rem; align-items: flex-start; }
.course-list-panel .card { margin-bottom: 1rem; }
.course-builder-panel .placeholder { text-align: center; padding: 4rem; color: #888; }
.course-list { list-style: none; padding: 0; margin: 0; }
.course-list li { padding: 0.8rem 1rem; border-radius: 5px; cursor: pointer; border: 1px solid transparent; }
.course-list li:hover { background-color: #f8f9fa; }
.course-list li.selected { background-color: #e9ecef; border-color: #ccc; font-weight: bold; }
.module-card { margin-bottom: 1.5rem; }
.content-list { list-style: none; padding-left: 1rem; margin-top: 1rem; }
.content-item { background-color: #f8f9fa; padding: 0.5rem; border-radius: 4px; margin-bottom: 0.5rem; }
.content-item-empty { color: #888; font-style: italic; }
.add-content-form { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #eee; display: flex; gap: 0.5rem; align-items: center;}
.btn-small { padding: 0.5rem 1rem; }
/* General Styles from before */
.course-mgmt-container { max-width: 1200px; margin: 2rem auto; padding: 1rem; }
.card { background: #fff; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.form-group { margin-bottom: 1rem; }
label { display: block; margin-bottom: 0.5rem; font-weight: 500; }
input, textarea, select { width: 100%; padding: 0.75rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
.btn { background-color: #007bff; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 4px; cursor: pointer; }
.btn-secondary {
  display: inline-block;
  background-color: #6c757d;
  margin-bottom: 1.5rem;
  text-decoration: none;
}
.message { padding: 1rem; border-radius: 4px; text-align: center; position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); }
.success { background-color: #d4edda; color: #155724; }
.error { background-color: #f8d7da; color: #721c24; }

</style>