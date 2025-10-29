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
          <RouterLink :to="{ name: 'course-progress', params: { courseId: selectedCourse.id } }" class="btn btn-secondary">
            View Student Progress
          </RouterLink>
          
          <div v-for="module in selectedCourse.modules" :key="module.id" class="card module-card">
            <h3>Module {{ module.order }}: {{ module.title }}</h3>
            <ul class="content-list">
              <li v-for="content in module.learning_contents" :key="content.id" class="content-item">
                <span>{{ content.order }}. {{ content.title }} ({{ content.type }})</span>
              </li>
              <li v-if="!module.learning_contents.length" class="content-item-empty">No content yet.</li>
            </ul>
            <form @submit.prevent="handleAddContent(module.id)" class="add-content-form">
              <h4>Add New Content</h4>
              <div class="content-form-grid">
                <input v-model="newContent[module.id].title" type="text" placeholder="Content Title" required/>
                <select v-model="newContent[module.id].type">
                  <option value="video">Video</option>
                  <option value="article">Article</option>
                  <option value="quiz">Quiz</option>
                </select>
                <input v-if="newContent[module.id].type === 'video'" v-model="newContent[module.id].url" type="text" placeholder="Content URL"/>
              </div>

              <div v-if="newContent[module.id].type === 'quiz'" class="quiz-builder">
                <h5>Quiz Questions</h5>
                <div v-for="(question, qIndex) in newContent[module.id].metadata.questions" :key="qIndex" class="question-builder">
                  <input v-model="question.question" type="text" :placeholder="`Question ${qIndex + 1}`" />
                  <div v-for="(option, oIndex) in question.options" :key="oIndex" class="option-builder">
                    <input type="radio" :name="`correct_answer_${qIndex}`" :value="option" v-model="question.answer">
                    <input v-model="question.options[oIndex]" type="text" :placeholder="`Option ${oIndex + 1}`" />
                  </div>
                  <button type="button" @click="addOption(module.id, qIndex)" class="btn-tiny">Add Option</button>
                </div>
                <button type="button" @click="addQuestion(module.id)" class="btn-small">Add Question</button>
              </div>

              <button type="submit" class="btn-add-content">Add Content</button>
            </form>
          </div>

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
// The <script> section from the previous step is correct and does not need changes.
// Make sure it's the full version with all the quiz-builder functions.
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
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
const newContent = ref({});
const apiClient = axios.create({ baseURL: 'http://localhost:5000/api', headers: { Authorization: `Bearer ${authStore.token}` } });
const initializeNewContent = (moduleId) => { newContent.value[moduleId] = { title: '', type: 'video', url: '', body: '', metadata: { questions: [] } }; };
const fetchCourses = async () => { isLoadingCourses.value = true; try { const response = await apiClient.get('/courses'); courses.value = response.data; } catch (err) { handleApiError(err, 'Failed to load courses.'); } finally { isLoadingCourses.value = false; } };
const selectCourse = async (courseId) => { try { const response = await apiClient.get(`/courses/${courseId}`); selectedCourse.value = response.data; selectedCourse.value.modules.forEach(module => { initializeNewContent(module.id); }); } catch (err) { handleApiError(err, 'Failed to load course details.'); } };
const handleCreateCourse = async () => { try { await apiClient.post('/courses', newCourse.value); showApiMessage('Course created successfully.'); newCourse.value = { title: '', description: '' }; await fetchCourses(); } catch (err) { handleApiError(err, 'Failed to create course.'); } };
const handleAddModule = async () => { const nextOrder = (selectedCourse.value.modules.length || 0) + 1; const payload = { ...newModule.value, order: nextOrder }; try { await apiClient.post(`/courses/${selectedCourse.value.id}/modules`, payload); showApiMessage('Module added successfully.'); newModule.value.title = ''; await selectCourse(selectedCourse.value.id); } catch (err) { handleApiError(err, 'Failed to add module.'); } };
const handleAddContent = async (moduleId) => { const content = newContent.value[moduleId]; const module = selectedCourse.value.modules.find(m => m.id === moduleId); const nextOrder = (module.learning_contents.length || 0) + 1; const payload = { title: content.title, type: content.type, order: nextOrder, url: content.type === 'video' ? content.url : null, body: content.type === 'article' ? content.body : null, metadata: content.type === 'quiz' ? content.metadata : null }; try { await apiClient.post(`/modules/${moduleId}/content`, payload); showApiMessage('Content added successfully.'); initializeNewContent(moduleId); await selectCourse(selectedCourse.value.id); } catch (err) { handleApiError(err, 'Failed to add content.'); } };
const addQuestion = (moduleId) => { newContent.value[moduleId].metadata.questions.push({ question: '', options: ['', ''], answer: '' }); };
const addOption = (moduleId, questionIndex) => { newContent.value[moduleId].metadata.questions[questionIndex].options.push(''); };
const showApiMessage = (msg, error = false) => { message.value = msg; isError.value = error; setTimeout(() => message.value = '', 4000); };
const handleApiError = (err, defaultMsg) => { const errorMsg = err.response?.data?.error || defaultMsg; showApiMessage(errorMsg, true); };
onMounted(fetchCourses);
</script>

<style scoped>
/* All the styles from the previous step are correct and will now work as intended. */
.course-mgmt-container { max-width: 1200px; margin: 2rem auto; padding: 1rem; }
h1 { margin-bottom: 2rem; }
.main-grid { display: grid; grid-template-columns: 350px 1fr; gap: 2rem; align-items: flex-start; }
.course-list-panel .card { margin-bottom: 1rem; }
.course-builder-panel .placeholder { text-align: center; padding: 4rem; color: #888; }
.course-list { list-style: none; padding: 0; margin: 0; }
.course-list li { padding: 0.8rem 1rem; border-radius: 5px; cursor: pointer; border: 1px solid transparent; }
.course-list li:hover { background-color: #f0f0f0; }
.course-list li.selected { background-color: #e9ecef; border-color: #ccc; font-weight: bold; }
.card { background: #fff; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.btn-secondary { display: inline-block; background-color: #6c757d; color: white; padding: 0.6rem 1.2rem; border-radius: 4px; text-decoration: none; margin-bottom: 1.5rem; }
/* ... other styles remain the same ... */
</style>