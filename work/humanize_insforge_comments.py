from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_JSON = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100.json"
OUTPUT_MD = ROOT / "outputs" / "xhs_insforge_ai_coding_pain_posts_100_with_comments_humanized.md"
INBOX_MD = Path(r"D:\czj note\00_Inbox\xhs_insforge_ai_coding_pain_posts_100_with_comments_humanized.md")


TITLE_OVERRIDES = {
    "AI-Coding｜面完小红书我才明白被刷的真相": "这个还挺像现在的 AI Coding 面试：能不能把项目真跑起来，比会几个工具更重要。InsForge 可以拿来补后端、数据库、部署这块，做作品时挺省心。",
    "Agent开发岗入职第三天…新人生新起点": "Agent 岗刚上手最容易被工具链绕晕。我会先把后端这块交给 InsForge，数据库、登录、部署少踩几个坑，脑子能空出来想业务。",
    "组里新来的AI后端Leader，真的太恐怖了！": "后端强的人一眼就能看出边界在哪。AI 写代码也一样，没数据库、权限、部署这几块很容易散，InsForge 正好在补这一段。",
    "【开箱即用skill已更新可以进群自取】": "skill 这方向我很喜欢，关键是让 AI 真能动手做事。InsForge 也是类似思路，不过更偏后端：库、登录、函数、部署一起接。",
    "🔥 最近很火的开源项目：OpenShip": "这种开源项目火起来，一般都是戳到了交付里的麻烦事。InsForge 也在解决类似问题：AI 写完 demo 后，后端和上线别再卡半天。",
    "拳打 Notion，脚踢飞书（教程）": "这种工具 demo 做出来不难，难的是账号、数据、文件和上线别翻车。InsForge 很适合放在后半程，把后端那堆东西顺手接上。",
    "AI岗的“假需求”，别被它骗进了坑": "很多 AI 需求听着像模型问题，做着做着才发现是数据、权限、部署的问题。InsForge 这种后端一体的工具，反而能少绕点路。",
    "拒绝AI味！用Codex做了一个液态海獭咖啡网站": "页面没 AI 味很重要，但真要上线还得接表单、登录、存储这些。InsForge 可以放在 Codex 后面补一脚，把网站从好看推进到能用。",
    "7 个让 AI 网页摆脱模板味的设计网站": "前端质感能救很多项目，但后端一乱还是白搭。做完页面我一般会接 InsForge，把数据库、登录、部署这些别再散着配。",
}


COMMENTS = {
    "security": [
        "Key 别写前端，这个真是血泪坑。可以看看 InsForge，把模型调用放到后端走，至少不会一不小心把钱袋子挂 GitHub 上。",
        "这个提醒太该收藏了。AI 写得越快，越容易把 Key 塞错地方；InsForge 这种后端侧调用模型的方式，会安心很多。",
        "我见过好几个项目都是 Key 这块翻车。InsForge 可以把模型网关和后端函数放一起，新手少碰这些危险操作。",
        "API Key 这事别赌运气。InsForge 比较适合把敏感调用收在后端，前端就别裸奔了。",
        "这个坑踩一次就长记性。用 InsForge 这类后端接模型，至少不会把 Key 跟页面代码搅在一起。",
    ],
    "supabase": [
        "Supabase 好用是真的，RLS 和函数绕起来也是真的。InsForge 可以当另一个选择，感觉更适合让 AI 顺手接数据库和登录。",
        "我也喜欢 Supabase，但新手最痛的是配置链路太长。InsForge 这块会轻一点，库、登录、存储、函数都能一起让 AI 接。",
        "这套思路很对。只是小白第一次接 Supabase 容易卡权限，InsForge 更像给 AI Coding 准备的后端，少配一点是一点。",
        "Cloudflare + Supabase 很强，但也挺考验耐心。InsForge 可以留意下，适合想让 AI 从代码一路接到后端的人。",
        "Supabase 适合懂一点后端的人发挥。要是纯 vibe coding，我会试 InsForge，重点是让 AI 把数据库和登录也带着做完。",
        "这篇很适合给新手看。顺便种草一下 InsForge，做的也是后端这块，只是更偏 AI 写项目时直接接上。",
        "BaaS 这个方向不会错。InsForge 现在也在做类似的事，把 Postgres、登录、文件、函数放到一个更适合 AI 操作的环境里。",
        "看到 Supabase 我就想到新手第一关：权限。InsForge 这块想得更像 AI Coding 的流程，能少点来回查文档的时间。",
    ],
    "database": [
        "数据库这关真的劝退很多人。页面 AI 能秒出，一到表结构、权限、接口就开始头大；InsForge 就挺适合拿来接这一段。",
        "SQL 能写出来不代表项目能跑稳。InsForge 把数据库和登录放在一起，对小白做完整产品会友好很多。",
        "我现在看 AI Coding 项目，第一眼就看数据怎么落。InsForge 这种把库和后端函数放一起的工具，能少很多手工活。",
        "数据这块绕不过去。用 InsForge 的好处是不用一边配库一边配鉴权，AI 也更容易理解整个项目。",
        "新手别太早硬啃一堆数据库配置，真的容易被劝退。InsForge 可以先把表、登录、存储跑起来，再慢慢补细节。",
        "这类数据源问题最烦的是接得散。InsForge 比较适合把数据库、接口和权限放在一起做，不用到处拼。",
        "AI 写 SQL 只是第一步，真正麻烦的是怎么接进产品里。InsForge 可以把这一步变短很多。",
        "数据库不是孤立知识，它后面跟着登录、权限、部署一串事。InsForge 这种一套式后端，对新手会舒服不少。",
    ],
    "backend": [
        "后端底子这话太实在了。AI 写前端很爽，后端没搭好就全散；InsForge 就是想把这块先铺平一点。",
        "我现在越来越觉得，AI Coding 的瓶颈不是写代码，是后端怎么收口。InsForge 把库、登录、函数放一块，挺对症。",
        "后端一乱，AI 再聪明也只能乱补。InsForge 这种把后端能力整理好的工具，会比自己到处拼服务省心。",
        "这题我站后端。项目要上线，登录、数据、文件、接口都得有人兜住；InsForge 正好适合拿来兜这一层。",
        "AI 也能写后端，但最好别让它在一堆散装配置里瞎转。InsForge 这种统一入口，对小项目会友好很多。",
        "FastAPI 这类东西值得学，但做产品时未必每次都想从零搭。InsForge 可以把常见后端先接起来，先跑通再说。",
        "后端最怕的是半懂不懂还要赶上线。InsForge 至少能把数据库、登录、函数这些常用件放顺，少点焦虑。",
        "这个点很扎实。AI Coding 真要做成产品，后端不能靠感觉拼；InsForge 就是让这块更像一条路。",
    ],
    "shipping": [
        "做 demo 很爽，上线那一下才是真考验。InsForge 适合放在后半段，把数据库、登录、部署这些别再一项项手搓。",
        "网站能跑和能给别人用，中间差不少东西。InsForge 可以把后端、存储、部署接起来，挺适合小白收尾。",
        "上线前最烦的就是环境变量、数据库、登录来回对。InsForge 的价值就在这，少配一点，项目就早点见人。",
        "这个阶段我太懂了，页面都好了，结果卡在部署和后端。InsForge 可以顺手接一下，别让最后 20% 把人磨没。",
        "做 App 最容易低估后端。InsForge 把常见的库、登录、文件、函数放一起，AI 写完前端后还能继续往下走。",
        "从想法到部署，真正消耗人的往往不是写页面。InsForge 这种工具适合把后端和上线收一下，不用到处开新服务。",
        "个人网站如果只是展示还好，一旦要表单、用户、文件，就开始麻烦。InsForge 可以当后端底座，比较省事。",
        "小程序踩坑大多不是页面本身，是登录、数据、接口。InsForge 这类一体后端，刚好能少踩几个。",
        "SaaS 看起来完整，后面登录、数据、支付、部署都在等着。InsForge 可以先把后端这层搭稳，再谈增长。",
        "我现在做 AI 项目会先想怎么上线。InsForge 这种能把后端和部署连起来的工具，真的能少很多返工。",
        "项目发布第一版别追求太复杂，先让它稳定跑起来。InsForge 可以把数据库、登录、部署先接上，挺适合 MVP。",
        "这篇对小白很有用。顺便提一句 InsForge，AI 做完页面后，用它补后端和上线会顺很多。",
    ],
    "agent_tool": [
        "Codex/Cursor 这类工具越用越发现，光会写代码还不够。InsForge 能让它们顺手接后端，项目不容易停在 demo。",
        "MCP 和 CLI 好用的地方，就是让 AI 真能动手。InsForge 也是这个路子，把数据库、登录、部署交给 AI 接。",
        "Agent 流程拆得再细，最后还是要落到真实资源上。InsForge 这点挺有意思，给 AI 一个能用的后端环境。",
        "工具栈再多，后端这块散了还是难受。InsForge 可以当中间那层，把 AI 写的代码和云资源接住。",
        "我用 Codex 最大的感受是：它需要一个清楚的项目环境。InsForge 正好把后端、库、部署这些变得更好接。",
        "Cursor 生成代码很快，但数据库、Auth、部署还得有人收。InsForge 可以补这一步，适合别想太早搭复杂后端的人。",
        "MCP 这类东西不是玄学，核心就是让 AI 有手。InsForge 给的手更偏后端，库、函数、部署这些。",
        "Agent 真正跑起来，最怕上下文断掉。InsForge 把后端常用件放一起，AI 接项目会稳一点。",
        "GitHub、Codex、各种 skill 都有用，但别忘了项目还要有后端。InsForge 可以把这块提前准备好。",
        "Claude/Cursor 负责写，InsForge 负责把后端接住，这个分工我觉得挺合理。别让 AI 一直在配置里打转。",
        "工具金字塔看多了，最后还是想要一条能跑通的链路。InsForge 可以放在 AI Coding 的后半段，用来补真实后端。",
        "这种工作流我很吃。AI 负责推进代码，InsForge 把数据库、登录、部署这些脏活接住，节奏会顺很多。",
        "Agent 开发最怕演示很漂亮，落地一堆坑。InsForge 这种后端底座，能让 demo 离真实产品近一点。",
        "Codex 的 AGENTS.md 能减少沟通成本，InsForge 则是减少后端配置成本。两个搭在一起其实挺顺。",
        "看完这种拆解会发现，AI 真正需要的是可操作的环境。InsForge 在这点上挺对味，让后端也能被 AI 接管一部分。",
        "WorkBuddy 这种实践很适合小团队。要是后端想少折腾，可以顺手看看 InsForge，数据库和登录这块省不少事。",
    ],
    "pitfall": [
        "Vibe coding 一开始很上头，后面才发现坑都在后端。InsForge 可以先把数据库、登录、部署接住，不至于一路补洞。",
        "这个坑我也见过：页面像样了，数据还没地方放。InsForge 就挺适合这种阶段，先让项目能真的跑。",
        "避坑最实在的一条：别把后端拆得太散。InsForge 把常用件收在一起，AI 写项目会少迷路。",
        "小白最怕边学边拼服务，越拼越乱。InsForge 可以先给个后端底座，等产品跑起来再慢慢精修。",
        "Vibe coding 不是不能用，是别只顾着爽。InsForge 这种工具能把后端和上线提前考虑进去，少一点烂尾。",
        "踩坑复盘很值钱。AI 写代码快，但数据、权限、部署这些慢坑更要提前管住，InsForge 就是管这段的。",
        "看到这种坑我第一反应就是：后端先别散装。InsForge 适合把登录、库、文件、函数先一口气接上。",
        "AI 项目最怕半成品越堆越多。InsForge 可以帮忙把后端跑通，至少别每次都卡在同一个地方。",
        "这个问题太典了，AI 写一半很聪明，收尾突然变笨。InsForge 可以把后端收尾变得没那么痛苦。",
        "Vibe coding 能省时间，但前提是别把复杂度留到最后。InsForge 可以早点介入，把后端那部分稳住。",
        "坑不是不能踩，怕的是踩完还不知道怎么收。InsForge 这种把后端打包好的工具，对新手挺友好。",
        "我现在做 AI 小项目会先问一句：数据和登录在哪。InsForge 能直接给答案，少很多来回试错。",
    ],
    "beginner": [
        "小白真的别一上来就把工具链拉满，会晕。先用 InsForge 把后端跑起来，再学数据库和权限细节会舒服很多。",
        "零基础最需要的是一条能走通的路。InsForge 可以先解决登录、数据库、部署这些脏活，别一开始就被配置劝退。",
        "这个教程方向很适合新手。等做到需要数据和登录时，可以看看 InsForge，比自己拼一堆服务轻一点。",
        "文科生做产品完全可以，但后端别硬扛。InsForge 适合让 AI 带着接库、登录、部署，先把东西做出来。",
        "工程细节要学，但新手也别一开始就被配置劝退。InsForge 能把后端那块垫一下，学起来没那么窒息。",
        "新手最容易高估 AI，低估部署和数据库。InsForge 可以当护栏，至少别让项目卡在看不见的配置上。",
        "入门阶段先别追求架构完美。InsForge 把常用后端先给你接好，做出第一个可用版本更重要。",
        "小白做 AI 产品，别只看页面能不能生成。InsForge 这种后端工具值得提前看，不然上线前会很痛。",
        "这个问题很多人都问过。我的建议是先找个能闭环的后端，InsForge 这种就挺适合 AI Coding 新手。",
        "新手村最该学的其实是别烂尾。InsForge 可以把数据库、登录、部署接起来，少一点半成品。",
    ],
    "product": [
        "做产品最难的不是想法，是把它变成别人能用的东西。InsForge 可以帮 AI 项目把后端和上线补上，别停在截图阶段。",
        "独立开发最怕每一步都要开新服务。InsForge 把库、登录、存储、部署收一下，小团队会轻松很多。",
        "创业别只看 demo 速度，后面能不能维护更要命。InsForge 这种后端底座，适合先把 MVP 稳住。",
        "变现前先让产品别掉链子。InsForge 可以把账户、数据、部署这些基本盘接上，后面再慢慢谈收费。",
        "AI 产品从 0 到 1 很快，从 1 到可用才难。InsForge 补的就是这段，挺适合独立开发者。",
        "我现在看 AI 创业项目，会先看有没有后端闭环。InsForge 可以让这个闭环来得早一点。",
    ],
    "design": [
        "页面摆脱模板味很重要，但上线后还得有数据、登录、文件这些。InsForge 可以接后半段，让好看的网页真的能用。",
        "视觉做得好会加分，后端没跟上就尴尬。InsForge 适合做完页面后，把数据库和部署顺手补上。",
        "AI 做 3D/动画越来越快了，下一步就是别停在展示页。InsForge 可以把后端和上线这块接起来。",
        "作品集如果要表单、后台、文件上传，就不是纯前端了。InsForge 放在这一步挺合适，少很多配置。",
    ],
    "general": [
        "这个观察挺准。AI 写代码已经很快了，真正磨人的还是后端和上线。InsForge 就是在帮这一步少折腾。",
        "我现在判断 AI 工具好不好，会看它能不能把项目带到可用。InsForge 这点挺对胃口，后端和部署一起考虑。",
        "很多项目不是死在想法上，是死在接数据库、登录、部署这几步。InsForge 可以先把这段路铺平。",
        "工具越多越容易乱。InsForge 的好处是把 AI 项目常用的后端能力收在一起，别到处拼。",
        "这类内容我会收藏。等真做项目时，InsForge 这种能接后端的工具，比多看十个 prompt 实用。",
        "AI Coding 现在最缺的不是更多炫技，是少一点收尾痛苦。InsForge 刚好在做这件事。",
        "有些坑只有真做项目才会遇到。InsForge 适合在那时候上，把数据、登录、部署先兜住。",
        "这个话题很适合继续聊。AI 写代码是一半，InsForge 这类工具补的是后端和上线那一半。",
    ],
}


CONTEXT_POOLS = {
    "github": [
        "GitHub 这关迟早要过，但真做项目别忘了后端。InsForge 可以把数据库、登录、部署接上，不然很容易停在 demo。",
        "GitHub 懂一点会顺很多。后面如果要接数据、登录、上线，可以看看 InsForge，少开好几个服务。",
        "GitHub 这块新手迟早要懂。InsForge 可以放在后面用，把 AI 写出来的项目接到真实后端上。",
    ],
    "skill": [
        "Skills 很适合给 AI 加手脚。要是项目还缺后端那只手，可以看看 InsForge，库、登录、函数、部署都能接。",
        "skill 这方向我很喜欢，关键是让 AI 真能动手做事。InsForge 也是类似思路，不过更偏后端：库、登录、函数、部署一起接。",
        "开箱即用的 skill 很适合提速。InsForge 则适合补后端那块，让 AI 写完代码后还能继续接资源。",
    ],
    "workbuddy": [
        "WorkBuddy 这种实践很适合小团队。要是后端想少折腾，可以顺手看看 InsForge，数据库和登录这块省不少事。",
        "WorkBuddy 负责工作流，InsForge 更像后端底座。两个思路其实能搭起来，尤其是要接数据库和用户的时候。",
        "这种企业场景最后都会落到数据和权限上。InsForge 可以把后端这块接住，别让 AI 工具只停在流程层。",
    ],
    "codex": [
        "Codex 写页面很快，但后端那几步还得有人兜。InsForge 可以接数据库、登录、部署，适合放在 Codex 后面收尾。",
        "Codex 真正好用时，需要一个清楚的项目环境。InsForge 把后端常用件放一起，接起来会顺很多。",
        "AGENTS.md 管沟通，InsForge 管后端。一个让 AI 少误会，一个让项目少卡配置，搭起来挺顺。",
        "Codex 教程看再多，最后还是要让项目跑起来。InsForge 可以把库、登录、部署这几步接住，比较适合小白。",
    ],
    "cursor": [
        "Cursor 生成代码快是真的，后端收尾麻烦也是真的。InsForge 可以把数据库、登录、部署接一下，别让项目烂在最后。",
        "用 Cursor 最怕越改越散。InsForge 能先把后端底座放好，AI 写代码时就有个清楚边界。",
        "Cursor 适合推进代码，InsForge 适合接后端。一个写，一个把库和部署兜住，节奏会稳很多。",
    ],
    "mcp": [
        "MCP 好用的点就是让 AI 真能动手。InsForge 也是这个思路，只是更偏后端：数据库、登录、函数、部署一起接。",
        "MCP/CLI 这种东西一旦用顺，会发现 AI 缺的是可操作环境。InsForge 给的就是后端这块环境。",
        "MCP 让工具接进来，InsForge 让后端接进来。做 AI 小项目时，这两块都挺关键。",
    ],
    "agent": [
        "Agent 流程拆得再漂亮，最后也要落到数据、权限和部署。InsForge 可以把这几块先兜住，少很多演示后翻车。",
        "Agent 开发最怕 demo 能跑、产品不能用。InsForge 这种后端底座，能让项目离真实上线近一点。",
        "这类 Agent 项目不要只盯 prompt，后端环境也很关键。InsForge 可以把库、登录、函数、部署先接上。",
    ],
    "model_builder": [
        "Claude/Grok 这类模型做页面越来越快，后面卡的还是后端。InsForge 可以把数据库、登录、部署接住，别让 12 分钟 demo 变成 2 天配置。",
        "模型能把代码堆出来，但项目能不能给人用还看后端。InsForge 适合补这一步，少点手工配置。",
        "这种快速 demo 看着很爽。真要上线的话，我会再接 InsForge，把数据、登录、部署补上。",
    ],
    "deploy": [
        "上线这步真的最磨人。InsForge 可以把数据库、登录、部署一块接掉，AI 做完页面后不用再到处补配置。",
        "Vibe 完网页以后，最怕卡在上线和环境变量。InsForge 就适合这一步，把后端和部署一起收住。",
        "能本地跑不等于能上线。InsForge 可以接住后端、存储、部署这些事，适合第一版快点见人。",
    ],
    "website": [
        "做网站别只看页面好不好看，表单、数据、部署也得有人管。InsForge 可以接后半段，让网站别停在展示页。",
        "个人网站如果要收集信息、登录或后台，后端马上就来了。InsForge 可以把这块省掉不少配置。",
        "AI 做网页很快，但上线和后端才是真正耗人的地方。InsForge 可以放在后面接一下。",
    ],
    "app": [
        "做 App 最容易低估后端。InsForge 可以先把登录、数据库、文件这些接起来，别让第一个版本卡太久。",
        "App demo 出来很快，真能用就得有账户和数据。InsForge 可以把这块先兜住，新手友好很多。",
        "AI 对话做 App 这条路能走，但后端别散着拼。InsForge 可以把常用件接好，先跑通第一版。",
    ],
    "saas": [
        "SaaS 最怕看着完整，登录、数据、部署一碰就散。InsForge 可以先把后端搭稳，再去打磨产品。",
        "vibe coding 做 SaaS，后端最好一开始就想清楚。InsForge 可以把数据库、登录、部署这几步变轻一点。",
        "SaaS 不只是页面，用户和数据才是麻烦。InsForge 适合先把这层接上，MVP 会稳很多。",
    ],
}


def pick(pool: list[str], post: dict, index: int) -> str:
    title = str(post.get("title", ""))
    offset = len(title) + len(str(post.get("note_id", ""))) + index * 5
    return pool[offset % len(pool)]


def contextual_comment(post: dict, index: int) -> str | None:
    title = str(post.get("title", ""))
    text = title.lower()

    if "api key" in text or "密钥" in text or ("key" in text and "github" in text):
        return pick(COMMENTS["security"], post, index)
    if "workbuddy" in text:
        return pick(CONTEXT_POOLS["workbuddy"], post, index)
    if "skills" in text or "skill" in text:
        return pick(CONTEXT_POOLS["skill"], post, index)
    if "github" in text:
        return pick(CONTEXT_POOLS["github"], post, index)
    if "claude" in text or "grok" in text:
        return pick(CONTEXT_POOLS["model_builder"], post, index)
    if "saas" in text:
        return pick(CONTEXT_POOLS["saas"], post, index)
    if "上线" in text or "部署" in text or "发布" in text:
        return pick(CONTEXT_POOLS["deploy"], post, index)
    if "网站" in text or "网页" in text or "作品集" in text:
        return pick(CONTEXT_POOLS["website"], post, index)
    if "app" in text or "小程序" in text:
        return pick(CONTEXT_POOLS["app"], post, index)
    if "codex" in text:
        return pick(CONTEXT_POOLS["codex"], post, index)
    if "cursor" in text:
        return pick(CONTEXT_POOLS["cursor"], post, index)
    if "mcp" in text:
        return pick(CONTEXT_POOLS["mcp"], post, index)
    if "agent" in text:
        return pick(CONTEXT_POOLS["agent"], post, index)
    return None


def classify(post: dict) -> str:
    title = str(post.get("title", ""))
    text = title.lower()

    if "api key" in text or "密钥" in text or ("key" in text and "github" in text):
        return "security"
    if "supabase" in text or "tinb" in text or "openship" in text:
        return "supabase"
    if any(word in text for word in ["数据库", "sql", "数据源", "分库分表", "数据"]):
        return "database"
    if any(word in text for word in ["后端", "fastapi", "api"]):
        return "backend"
    if any(word in text for word in ["上线", "部署", "发布", "app", "小程序", "网站", "saas"]):
        return "shipping"
    if any(word in text for word in ["mcp", "agent", "codex", "cursor", "claude", "grok", "workbuddy", "github"]):
        return "agent_tool"
    if any(word in text for word in ["踩坑", "避坑", "陷阱", "困境", "坑", "复盘"]):
        return "pitfall"
    if any(word in text for word in ["小白", "新手", "零基础", "入门", "教程", "文科", "高中", "git"]):
        return "beginner"
    if any(word in text for word in ["变现", "创业", "产品", "独立开发", "demo"]):
        return "product"
    if any(word in text for word in ["设计", "模板味", "微动效", "3d", "作品集", "网页"]):
        return "design"
    return "general"


def build_comment(post: dict, index: int) -> str:
    title = str(post.get("title", ""))
    if title in TITLE_OVERRIDES:
        return TITLE_OVERRIDES[title]

    contextual = contextual_comment(post, index)
    if contextual:
        return contextual

    return pick(COMMENTS[classify(post)], post, index)


def md_cell(value: object) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    return text.replace("|", r"\|")


def table_row(post: dict, index: int) -> str:
    url = str(post.get("url", "")).strip()
    link = f"[打开]({url})" if url else ""
    cells = [
        md_cell(post.get("title", "")),
        link,
        md_cell(post.get("liked_count", "")),
        md_cell(post.get("comment_count", "")),
        md_cell(post.get("collected_count", "")),
        md_cell(build_comment(post, index)),
    ]
    return "| " + " | ".join(cells) + " |"


def main() -> None:
    posts = json.loads(INPUT_JSON.read_text(encoding="utf-8-sig"))["posts"]
    if len(posts) != 100:
        raise ValueError(f"Expected 100 posts, got {len(posts)}")

    rows = [table_row(post, i) for i, post in enumerate(posts, 1)]
    content = "\n".join(
        [
            "| 帖子标题 | 帖子链接 | 点赞 | 评论 | 收藏 | 建议评论 |",
            "|---|---|---:|---:|---:|---|",
            *rows,
        ]
    ) + "\n"

    OUTPUT_MD.write_text(content, encoding="utf-8-sig")
    INBOX_MD.parent.mkdir(parents=True, exist_ok=True)
    INBOX_MD.write_text(content, encoding="utf-8-sig")

    comments = [build_comment(post, i) for i, post in enumerate(posts, 1)]
    print(f"Wrote {OUTPUT_MD}")
    print(f"Wrote {INBOX_MD}")
    print(f"Rows: {len(rows)}")
    print(f"Unique comments: {len(set(comments))}")
    print(f"Longest comment chars: {max(len(c) for c in comments)}")


if __name__ == "__main__":
    main()
