/* Explanatory UI only. No collection, network requests or persistent state. */
document.querySelectorAll('[data-impact-tab]').forEach((tab,index,tabs)=>{
  const select=()=>{
    tabs.forEach(other=>{
      const active=other===tab;
      other.setAttribute('aria-selected',String(active));
      other.tabIndex=active?0:-1;
      const panel=document.getElementById(other.getAttribute('aria-controls'));
      if(panel)panel.hidden=!active;
    });
  };
  tab.addEventListener('click',select);
  tab.addEventListener('keydown',event=>{
    let next;
    if(event.key==='ArrowRight')next=(index+1)%tabs.length;
    else if(event.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;
    else if(event.key==='Home')next=0;
    else if(event.key==='End')next=tabs.length-1;
    else return;
    event.preventDefault();tabs[next].click();tabs[next].focus();
  });
});
