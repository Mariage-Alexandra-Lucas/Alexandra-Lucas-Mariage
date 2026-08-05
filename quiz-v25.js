(() => {
  const previousRefresh=refresh, previousGameView=gameView, previousProfileView=profileView, previousShell=shell;
  state.quiz={currentIndex:-1,current:null,scores:{},questions:[],tables:['Guadeloupe','Île Maurice','Maldives','Mexique']};
  let quizTimer=null, quizSignature='';
  const controller=()=>state.user?.role==='dj';
  const quizEsc=value=>esc(value||'');

  async function loadQuiz(){
    if(!state.user)return;
    state.quiz=await api('/api/v25/quiz').catch(()=>state.quiz);
  }
  refresh=async function(){await previousRefresh();await loadQuiz()};

  function scoreBoard(editable=false){
    return `<div class="quiz-scores">${(state.quiz.tables||[]).map(table=>`<article><span>${quizEsc(table)}</span><b>${Number(state.quiz.scores?.[table]||0)}</b>${editable?`<div><button data-score-table="${quizEsc(table)}" data-delta="-1">−</button><button data-score-table="${quizEsc(table)}" data-delta="1">＋</button></div>`:''}</article>`).join('')}</div>`;
  }

  function guestQuiz(){
    const q=state.quiz.current;
    if(!q)return `<section class="card quiz-live"><div class="section-title">Quiz des mariés</div><h2>En attente du DJ</h2><p>La première question apparaîtra automatiquement ici.</p></section>`;
    const response=q.tableResponse?.answer;
    if(q.status==='open')return `<section class="card quiz-live"><div class="question-number">Question ${q.number}/15</div><h2>${quizEsc(q.text)}</h2><p>Discutez avec votre table puis choisissez votre réponse commune.</p><div class="elle-lui"><button data-quiz-answer="elle" class="${response==='elle'?'selected':''}">Elle</button><button data-quiz-answer="lui" class="${response==='lui'?'selected':''}">Lui</button></div>${response?`<p class="table-answer">Réponse de ${quizEsc(state.user.table)} : <b>${response==='elle'?'Elle':'Lui'}</b><br><small>Dernière modification par ${quizEsc(q.tableResponse.updatedBy)}</small></p>`:''}</section>${scoreBoard()}`;
    if(q.status==='closed')return `<section class="card quiz-live"><div class="question-number">Question ${q.number}/15</div><h2>${quizEsc(q.text)}</h2><div class="answers-closed">Réponses clôturées</div><p>Votre table a répondu : <b>${response?response==='elle'?'Elle':'Lui':'Aucune réponse'}</b></p><p>Le DJ va révéler la bonne réponse.</p></section>${scoreBoard()}`;
    if(q.status==='revealed')return `<section class="card quiz-live revealed"><div class="question-number">Question ${q.number}/15</div><h2>${quizEsc(q.text)}</h2><p>La bonne réponse était :</p><div class="correct-answer">${q.correctAnswer==='elle'?'Elle':'Lui'}</div><p>Réponse de votre table : <b>${response?response==='elle'?'Elle':'Lui':'Aucune'}</b> ${response===q.correctAnswer?'✅':'❌'}</p></section>${scoreBoard()}`;
    return `<section class="card quiz-live"><h2>Question prête</h2><p>Le DJ va bientôt ouvrir les réponses.</p></section>`;
  }

  function controlPanel(){
    const q=state.quiz.current,responses=q?.responses||{};
    const options=(state.quiz.questions||[]).map((item,index)=>`<option value="${index}" ${state.quiz.currentIndex===index?'selected':''}>${index+1}. ${quizEsc(item.text||'Question non configurée')}</option>`).join('');
    return `<section class="card quiz-control"><div class="section-title">Console DJ</div><h2>Animation Elle ou Lui</h2><button class="btn launch-quiz" data-quiz-control="launch">Lancer le jeu</button><select class="field" id="quiz-question-select">${options}</select><div class="control-buttons"><button class="btn" data-quiz-control="start">Lancer la question</button><button class="btn secondary" data-quiz-control="close" ${!q||q.status!=='open'?'disabled':''}>Clôturer le vote et afficher la réponse</button></div>${q?`<div class="dj-question"><span>Question ${q.number}/15 — ${quizEsc(q.status)}</span><h3>${quizEsc(q.text)}</h3><form id="correct-answer-form"><label>Bonne réponse</label><div class="answer-correction"><select class="field" name="answer"><option value="elle" ${q.correctAnswer==='elle'?'selected':''}>Elle</option><option value="lui" ${q.correctAnswer==='lui'?'selected':''}>Lui</option></select><button class="btn secondary">Corriger</button></div></form></div><p class="vote-progress">${Object.keys(responses).length}/4 tables ont répondu</p>`:'<p>Le jeu est prêt. Lancez-le, puis choisissez la première question.</p>'}${scoreBoard(false)}</section>`;
  }

  function quizEditor(){
    if(!(state.user?.role==='superadmin'&&state.adminView))return '';
    const questions=state.quiz.questions?.length===15?state.quiz.questions:Array.from({length:15},(_,i)=>({number:i+1,text:'',answer:'elle'}));
    return `<section class="card quiz-editor"><div class="section-title">Configuration du quiz DJ</div><h2>Les 15 questions Elle ou Lui</h2><p>Les réponses et scores seront remis à zéro lors de l’enregistrement.</p><form id="quiz-config-form"><div class="question-editor-list">${questions.map((q,i)=>`<label><b>${i+1}</b><textarea name="question-${i}" rows="2" maxlength="280" required placeholder="Écrivez la question ${i+1}">${quizEsc(q.text)}</textarea><select name="answer-${i}"><option value="elle" ${q.answer==='elle'?'selected':''}>Elle</option><option value="lui" ${q.answer==='lui'?'selected':''}>Lui</option></select></label>`).join('')}</div><button class="btn">Enregistrer les 15 questions</button></form><button class="btn danger" id="reset-quiz">Remettre réponses et scores à zéro</button></section>`;
  }

  gameView=function(){
    const base=previousGameView().replace(/<section class="card locked"><h2>Quiz des mariés<\/h2>.*?<\/section>$/,'');
    return `${controller()?controlPanel():guestQuiz()}${base}`;
  };
  profileView=function(){return `${previousProfileView()}${quizEditor()}`};

  async function quizControl(action){
    const index=Number(document.querySelector('#quiz-question-select')?.value||0);
    state.quiz=await api('/api/v25/quiz/control',{method:'POST',body:JSON.stringify({action,index})});render();
  }
  function bindQuiz(){
    app.querySelectorAll('[data-quiz-answer]').forEach(button=>button.onclick=async()=>{try{state.quiz=await api('/api/v25/quiz/answer',{method:'POST',body:JSON.stringify({answer:button.dataset.quizAnswer})});render();toast(`Réponse commune de ${state.user.table} mise à jour`)}catch(e){toast(e.message)}});
    app.querySelectorAll('[data-quiz-control]').forEach(button=>button.onclick=()=>quizControl(button.dataset.quizControl).catch(e=>toast(e.message)));
    app.querySelectorAll('[data-score-table]').forEach(button=>button.onclick=async()=>{state.quiz=await api('/api/v25/quiz/score',{method:'POST',body:JSON.stringify({table:button.dataset.scoreTable,delta:Number(button.dataset.delta)})});render()});
    app.querySelector('#correct-answer-form')?.addEventListener('submit',async event=>{event.preventDefault();try{state.quiz=await api('/api/v25/quiz/control',{method:'POST',body:JSON.stringify({action:'correct',answer:new FormData(event.target).get('answer')})});render();toast('Bonne réponse corrigée')}catch(e){toast(e.message)}});
    app.querySelector('#quiz-config-form')?.addEventListener('submit',async event=>{event.preventDefault();const form=new FormData(event.target),questions=Array.from({length:15},(_,i)=>({text:form.get(`question-${i}`),answer:form.get(`answer-${i}`)}));try{state.quiz=await api('/api/v25/quiz/config',{method:'POST',body:JSON.stringify({questions})});render();toast('Les 15 questions sont enregistrées')}catch(e){toast(e.message)}});
    app.querySelector('#reset-quiz')?.addEventListener('click',async()=>{if(!confirm('Effacer toutes les réponses et remettre les scores à zéro ?'))return;state.quiz=await api('/api/v25/quiz/control',{method:'POST',body:JSON.stringify({action:'reset'})});render();toast('Quiz remis à zéro')});
  }
  function startPolling(){clearInterval(quizTimer);quizSignature=JSON.stringify(state.quiz);quizTimer=setInterval(async()=>{const next=await api('/api/v25/quiz').catch(()=>null);if(next&&JSON.stringify(next)!==quizSignature){state.quiz=next;quizSignature=JSON.stringify(next);render()}},3000)}
  shell=function(){
    if(state.user?.role==='dj'){
      app.innerHTML=`<main class="shell dj-only"><header class="dj-header"><div><span>Animation</span><strong>Elle ou Lui</strong></div><button class="btn secondary" id="logout">Se déconnecter</button></header>${controlPanel()}</main>`;
      app.querySelector('#logout').onclick=logout;bindQuiz();startPolling();return;
    }
    previousShell();bindQuiz();clearInterval(quizTimer);if(state.tab==='game')startPolling();
  };
  window.MARIAGE_QUIZ_V25={editor:quizEditor,bind:bindQuiz};
  window.addEventListener('beforeunload',()=>clearInterval(quizTimer));
  if(state.user)loadQuiz().finally(render);
})();
