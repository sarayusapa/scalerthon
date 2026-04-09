sending u the requirements of this again, make and implement whats already not done: KEY REQUIREMENTS AT A GLANCE             
  Must simulate a real-world task (not games or toys)                                                                           
  Implement full OpenEnv spec: typed models, step()/reset()/state(), openenv.yaml                                               
  Minimum 3 tasks with agent graders (easy → medium → hard, scores/reward 0.0–1.0)                                              
  Meaningful reward function with partial progress signals                                                                      
  Baseline inference script with reproducible scores                                                                            
  Deploy to Hugging Face Spaces + working Dockerfile                                                                            
  README with environment description, action/observation spaces, setup instructionsFUNCTIONAL REQUIREMENTS                     
  Real-world task simulation                                                                                                    
  The environment must simulate a task humans actually do. Not games, not toys. Examples: email triage, code review, data       
  cleaning, scheduling, customer support, content moderation.                                                                   
  OpenEnv spec compliance                                                                                                       
  Implement the full OpenEnv interface: typed Observation, Action, and Reward Pydantic models. step(action) → returns           
  observation, reward, done, info. reset() → returns initial observation. state() → returns current state. openenv.yaml with    
  metadata. Tested via openenv validate.                                                                                        
  Minimum 3 tasks with agent graders                                                                                            
  Each task defines a concrete objective an agent must accomplish, with a programmatic grader that scores performance           
  (0.0–1.0). Tasks should range: easy → medium → hard. Graders must have clear, deterministic success/failure criteria.         
  Meaningful reward function                                                                                                    
  Provides signal over the full trajectory (not just binary end-of-episode). Rewards partial progress toward task completion.   
  Penalizes clearly undesirable behavior (e.g. infinite loops, destructive actions).                                            
  Baseline inference script                                                                                                     
  Uses the OpenAI API client to run a model against the environment. Reads API credentials from environment variables           
  (OPENAI_API_KEY). Produces a reproducible baseline score on all 3 tasks.                                                      
  Detailed Requirements                                                                                                         
  NON-FUNCTIONAL REQUIREMENTS                                                                                                   
  Deploys to a Hugging Face Space                                                                                               
  Environment must run as a containerized HF Space tagged with openenv.                                                         
  Containerized execution                                                                                                       
  Must include a working Dockerfile. The environment should start cleanly with docker build + docker run.                       
  Documentation                                                                                                                 
  README must include: environment description and motivation, action and observation space definitions, task descriptions with 
   expected difficulty, setup and usage instructions, baseline scores.. scoring: PARAMETER                                      
  WEIGHT                                                                                                                        
  DESCRIPTION                                                                                                                   
  Real-world utility                                                                                                            
  30%                                                                                                                           
  Does the environment model a genuine task? Would someone actually use this to train or evaluate agents?                       
  Task & grader quality                                                                                                         
  25%                                                                                                                           
  A                                                                                                                             
  … +364 lines …                                                                                                                
  ttp_code}" -X POST \                                                                                                          
    -H "Content-Type: application/json" -d '{}' \                                                                               
    "$PING_URL/reset" --max-time 30 2>"$CURL_OUTPUT" || printf "000")                                                           
                                                                                                                                
  if [ "$HTTP_CODE" = "200" ]; then                                                                                             
    pass "HF Space is live and responds to /reset"                                                                              
  elif [ "$HTTP_CODE" = "000" ]; then                                                                                           
    fail "HF Space not reachable (connection failed or timed out)"                                                              
    hint "Check your network connection and that the Space is running."                                                         
    hint "Try: curl -s -o /dev/null -w '%%{http_code}' -X POST $PING_URL/reset"                                                 
    stop_at "Step 1"                                                                                                            
  else                                                                                                                          
    fail "HF Space /reset returned HTTP $HTTP_CODE (expected 200)"                                                              
    hint "Make sure your Space is running and the URL is correct."                                                              
    hint "Try opening $PING_URL in your browser first."                                                                         
    stop_at "Step 1"                                                                                                            
  fi                                                                                                                            
                                                                                                                                
  log "${BOLD}Step 2/3: Running docker build${NC} ..."                                                                          
                                                                                                                                
  if ! command -v docker &>/dev/null; then                                                                                      
    fail "docker command not found"                                                                                             
    hint "Install Docker: https://docs.docker.com/get-docker/"                                                                  
    stop_at "Step 2"                                                                                                            
  fi                                                                                                                            
                                                                                                                                
  if [ -f "$REPO_DIR/Dockerfile" ]; then                                                                                        
    DOCKER_CONTEXT="$REPO_DIR"                                                                                                  
  elif [ -f "$REPO_DIR/server/Dockerfile" ]; then                                                                               
    DOCKER_CONTEXT="$REPO_DIR/server"                                                                                           
  else                                                                                                                          
    fail "No Dockerfile found in repo root or server/ directory"                                                                
    stop_at "Step 2"                                                                                                            
  fi                                                                                                                            
                                                                                                                                
  log "  Found Dockerfile in $DOCKER_CONTEXT"                                                                                   
                                                                                                                                
  BUILD_OK=false                                                                                                                
  BUILD_OUTPUT=$(run_with_timeout "$DOCKER_BUILD_TIMEOUT" docker build "$DOCKER_CONTEXT" 2>&1) && BUILD_OK=true                 
                                                                                                                                
  if [ "$BUILD_OK" = true ]; then                                                                                               
    pass "Docker build succeeded"                                                                                               
  else                                                                                                                          
    fail "Docker build failed (timeout=${DOCKER_BUILD_TIMEOUT}s)"                                                               
    printf "%s\n" "$BUILD_OUTPUT" | tail -20                                                                                    
    stop_at "Step 2"                                                                                                            
  fi                                                                                                                            
                                                                                                                                
  log "${BOLD}Step 3/3: Running openenv validate${NC} ..."                                                                      
                                                                                                                                
  if ! command -v openenv &>/dev/null; then                                                                                     
    fail "openenv command not found"                                                                                            
    hint "Install it: pip install openenv-core"                                                                                 
    stop_at "Step 3"                                                                                                            
  fi                                                                                                                            
                                                                                                                                
  VALIDATE_OK=false                                                                                                             
  VALIDATE_OUTPUT=$(cd "$REPO_DIR" && openenv validate 2>&1) && VALIDATE_OK=true                                                
                                                                                                                                
  if [ "$VALIDATE_OK" = true ]; then                                                                                            
    pass "openenv validate passed"                                                                                              
    [ -n "$VALIDATE_OUTPUT" ] && log "  $VALIDATE_OUTPUT"                                                                       
  else                                                                                                                          
    fail "openenv validate failed"                                                                                              
    printf "%s\n" "$VALIDATE_OUTPUT"                                                                                            
    stop_at "Step 3"                                                                                                            
  fi                                                                                                                            
                                                                                                                                
  printf "\n"                                                                                                                   
  printf "${BOLD}========================================${NC}\n"                                                               
  printf "${GREEN}${BOLD}  All 3/3 checks passed!${NC}\n"                                                                       
  printf "${GREEN}${BOLD}  Your submission is ready to submit.${NC}\n"                                                          
  printf "${BOLD}========================================${NC}\n"                                                               
  printf "\n"                                                                                                                   
                                                                                                                                
  exit 0. the general task is to Build a complete, real-world OpenEnv environment that an AI agent can learn from through the   
  standard  step() / reset() / state()  API.. cook.