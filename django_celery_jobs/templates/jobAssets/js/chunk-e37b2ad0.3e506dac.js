(window["webpackJsonp"]=window["webpackJsonp"]||[]).push([["chunk-e37b2ad0"],{"84a9":function(t,a,n){},9406:function(t,a,n){"use strict";n.r(a);var s=function(){var t=this,a=t.$createElement,n=t._self._c||a;return n("div",{attrs:{id:"home"}},[n("el-row",{staticClass:"info-card"},[n("el-col",{attrs:{span:24}},[n("el-card",{staticClass:"box-card"},[n("div",{staticClass:"clearfix quick-navigation",attrs:{slot:"header"},slot:"header"},[n("i",{staticClass:"el-icon-link"}),n("span",[t._v(" 快捷操作")])]),n("div",{staticClass:"clearfix"},t._l(t.models,(function(a,s){return n("div",{key:a.name,staticClass:"quick-wrap"},[n("a",{attrs:{href:"javascript:;"},on:{click:function(n){return t.openLink(a.path)}}},[n("span",{staticClass:"icon",class:a.icon}),n("span",{staticClass:"card-name",domProps:{textContent:t._s(a.name)}})])])})),0)])],1)],1)],1)},e=[],c=n("5530"),i=n("2f62"),o=n("a18c"),r={name:"Dashboard",data:function(){return{models:[]}},mounted:function(){for(var t=["/"],a=0;a<o["a"].length;a++){var n=o["a"][a];if(-1===t.indexOf(n.path)){var s=n.path,e=n.children||[];if(e.length>0)for(var c=0;c<e.length;c++){var i=e[c];this.models.push({path:s+"/"+i.path,name:i.meta.title,icon:i.meta.icon})}}}},computed:Object(c["a"])({},Object(i["b"])(["name"])),methods:{openLink:function(t){this.$router.push(t)}}},l=r,d=(n("c4c6"),n("2877")),u=Object(d["a"])(l,s,e,!1,null,"52313d28",null);a["default"]=u.exports},c4c6:function(t,a,n){"use strict";n("84a9")}}]);