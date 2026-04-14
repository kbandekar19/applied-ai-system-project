# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**VibeMatcher 1.0** - A music recommender that matches songs to your mood and energy preferences.  

---

## 2. Intended Use  

VibeMatcher suggests the top 5 songs from a small music catalog that best match a user's preferred genre, mood, and energy level. It generates personalized music recommendations with transparent scoring explanations. This system is designed for classroom exploration and learning about recommendation algorithms, not for real users or commercial music streaming services.  

---

## 3. How the Model Works  

VibeMatcher scores each song by comparing it to user preferences across four dimensions. It gives points when the song's genre matches the user's favorite genre (+1.5 points), when the mood matches (+2 points), and when the energy level is similar to what the user wants (up to +4 points based on how close they are). Songs with positive, uplifting feelings get a small bonus (+1 point) if the user likes happy music. The system then ranks all songs by total score and shows the top 5 matches with explanations of why each song scored that way.

---

## 4. Data  

The system uses a small dataset of 18 songs with features like genre, mood, energy level, and musical characteristics. Genres include pop, rock, lofi, and many others, but some genres (like lofi) have more songs than others (like classical or metal). Moods range from happy and chill to intense and melancholic, with similar imbalances. Energy levels span from very calm (0.25) to very energetic (0.96). This dataset represents a limited sample of musical diversity and doesn't capture all possible music preferences or cultural contexts.  

---

## 5. Strengths  

VibeMatcher works well for users with common music preferences like pop, lofi, or rock music. It correctly identifies songs that match both genre and mood preferences, creating recommendations that feel intuitively right. The system handles edge cases gracefully without crashing, and its transparent scoring helps users understand why certain songs were recommended. The algorithm successfully balances different types of musical preferences (categorical like genre vs. numeric like energy) to create reasonable personalized recommendations.  

---

## 6. Limitations and Bias 

The system exhibits significant genre and mood distribution biases that create unfair recommendation quality across different user types. For instance, users who prefer "lofi" music receive much better recommendations since 3 out of 18 songs (16.7%) match this genre, while users preferring "metal," "classical," or "jazz" are limited to only 1 matching song each (5.6% of the dataset). This imbalance means some users get diverse, high-quality recommendations while others receive recommendations from an extremely limited pool. The experimental weight shift testing revealed that even small changes to scoring weights can dramatically alter recommendation fairness, with energy-focused users gaining advantages over genre-purists when energy weights are doubled. Additionally, the valence bonus feature exclusively benefits users who prefer "happy" music, potentially discriminating against users who enjoy melancholic, intense, or moody songs by systematically excluding them from this scoring enhancement.

---

## 7. Evaluation  

I tested the recommender system with seven distinct user profiles to evaluate its behavior across different musical preferences and edge cases. The standard profiles included "High-Energy Pop" (pop genre, happy mood, energy 0.8), "Chill Lofi" (lofi genre, chill mood, energy 0.4), and "Deep Intense Rock" (rock genre, intense mood, energy 0.9). These baseline tests verified the system could generate reasonable recommendations for typical user preferences.

What surprised me most was the system's sensitivity to small algorithmic changes. When I experimentally doubled the energy similarity weight and halved the genre weight, the recommendations completely reordered - songs that previously ranked low due to genre mismatches suddenly appeared at the top if they had good energy matches. This demonstrated how fragile the recommendation rankings are to scoring parameter tuning.

The adversarial profiles revealed additional insights: the "Conflicting: High Energy + Sad Mood" profile showed the system prioritizes available matching criteria (genre and energy) over impossible preferences, while the "Non-existent Genre" profile proved the algorithm gracefully degrades by focusing on mood and energy matches when genre preferences can't be satisfied. The "Extreme: Zero Energy + Happy" profile confirmed the system handles boundary values appropriately without crashing.

Overall, the evaluation showed the system works well for mainstream preferences but struggles with underrepresented genres and moods due to dataset limitations. The experimental weight testing validated that the original scoring balance was reasonable, as extreme weight shifts created unfair advantages for certain user types.

---

## 8. Future Work  

To improve VibeMatcher, I would expand the dataset to include more songs and better balance across genres and moods so all users get fair recommendations. I would add diversity controls to prevent the top recommendations from being too similar, ensuring users discover a variety of music. I would also implement user feedback mechanisms so the system can learn from what songs users actually like or dislike, making recommendations more personalized over time.  

---

## 9. Personal Reflection  

My biggest learning moment came when I discovered how sensitive recommendation algorithms are to seemingly small design decisions. When I experimentally doubled the energy weight and halved the genre weight, the entire recommendation rankings flipped - songs that were previously buried suddenly became top recommendations. This showed me how fragile these systems can be and how "tuning" parameters can inadvertently create or remove user discrimination.

AI tools like GitHub Copilot were incredibly helpful for rapid prototyping and explaining complex concepts. They helped me implement the scoring logic, generate comprehensive tests, and even write documentation. However, I had to double-check their suggestions when dealing with edge cases - for instance, Copilot initially suggested a simpler energy calculation that didn't handle boundary values properly, and I needed to verify the math worked correctly across the full 0-1 range.

What surprised me most was how a simple algorithm using just four features (genre, mood, energy, valence) could produce recommendations that genuinely "felt" right. Even with its limitations, VibeMatcher often suggested songs that matched my musical intuition. This made me realize that effective recommendations don't need complexity - they need the right balance of features that capture what users actually care about.

If I extended this project, I would explore collaborative filtering by adding user interaction data, implement diversity algorithms to prevent recommendation bubbles, and build an interactive web interface where users could adjust their preferences in real-time and see how recommendations change. I would also investigate how to make the system more inclusive by expanding the dataset to better represent diverse musical cultures and preferences.  
