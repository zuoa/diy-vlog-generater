// 显示加载动画
function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

// 隐藏加载动画
function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

// 处理表单提交
function handleFormSubmit(event, form) {
    event.preventDefault(); // 阻止默认表单提交
    
    showLoading();
    
    // 创建FormData对象
    const formData = new FormData(form);
    
    // 发送Ajax请求
    fetch(form.action, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        hideLoading();
        
        if (data.success && data.data && data.data.status_url) {
            // 跳转到状态页面
            window.location.href = data.data.status_url;
        } else {
            // 处理错误响应
            const errorMessage = data.message || '请求失败，请重试';
            alert('错误: ' + errorMessage);
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error:', error);
        alert('网络错误或服务器错误，请重试: ' + error.message);
    });
    
    return false; // 阻止表单的默认提交行为
}

// 切换模式
function switchMode(mode) {
    // 更新按钮状态
    document.querySelectorAll('.mode-btn').forEach(function(btn) { 
        btn.classList.remove('active'); 
    });
    event.target.classList.add('active');
    
    // 隐藏所有模式的表单
    const modes = ['two-video-mode', 'maozibi-mode', 'maobizi-score-mode', 'single-video-mode', 'img-mode'];
    modes.forEach(function(modeId) {
        const element = document.getElementById(modeId);
        if (element) {
            element.classList.add('hidden');
        }
    });
    
    // 显示选中的模式
    let targetModeId;
    switch(mode) {
        case 'two':
            targetModeId = 'two-video-mode';
            break;
        case 'maozibi':
            targetModeId = 'maozibi-mode';
            break;
        case 'maobizi-score':
            targetModeId = 'maobizi-score-mode';
            break;
        case 'single':
            targetModeId = 'single-video-mode';
            break;
        case 'img':
            targetModeId = 'img-mode';
            break;
    }
    
    if (targetModeId) {
        const targetElement = document.getElementById(targetModeId);
        if (targetElement) {
            targetElement.classList.remove('hidden');
        }
    }
}

// 生成二维码的函数 (使用qrcodejs库)
function generateQRCode(text, elementId, options = {}) {
    console.log('开始生成二维码:', elementId, '文本:', text, '选项:', options);
    
    const element = document.getElementById(elementId);
    if (!element) {
        console.error('找不到二维码容器元素:', elementId);
        return;
    }
    
    console.log('二维码容器元素找到:', element);
    console.log('容器样式:', window.getComputedStyle(element));
    
    // 检查是否已经生成过二维码
    if (element.dataset.qrGenerated === 'true') {
        console.log('二维码已存在，跳过生成:', elementId);
        return;
    }
    
    // 检查QRCode库是否可用
    if (!checkQRCodeLibrary()) {
        console.error('QRCode库未加载');
        element.innerHTML = '<div style="color: red; text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #fff5f5;">❌ QRCode库未加载<br/><small>请刷新页面重试</small></div>';
        return;
    }
    
    console.log('QRCode库已可用，版本信息:', typeof QRCode);
    
    // 彻底清空容器内容
    element.innerHTML = '';
    
    // 等待DOM更新后再生成二维码
    setTimeout(function() {
        try {
            const qrOptions = {
                text: text,
                width: options.width || 200,
                height: options.height || 200,
                colorDark: options.darkColor || '#000000',
                colorLight: options.lightColor || '#FFFFFF'
            };
            
            console.log('正在创建二维码，选项:', qrOptions);
            
            // 创建二维码
            new QRCode(element, qrOptions);
            
            // 标记已生成
            element.dataset.qrGenerated = 'true';
            console.log('二维码创建完成:', elementId);
            
            // 确保只有一个二维码元素
            setTimeout(function() {
                const qrElements = element.querySelectorAll('canvas, img');
                console.log('检查二维码元素数量:', qrElements.length);
                
                if (qrElements.length > 1) {
                    console.warn('发现多个二维码元素，移除多余的');
                    for (let i = 1; i < qrElements.length; i++) {
                        qrElements[i].remove();
                    }
                } else if (qrElements.length === 0) {
                    console.error('二维码生成失败，没有找到canvas或img元素');
                    element.innerHTML = '<div style="color: orange; text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #fffbf0;">⚠️ 二维码生成异常<br/><small>尝试刷新页面</small></div>';
                } else {
                    console.log('二维码生成成功，元素类型:', qrElements[0].tagName);
                    // 确保元素可见
                    qrElements[0].style.display = 'block';
                    qrElements[0].style.margin = '0 auto';
                }
            }, 200);
            
        } catch (error) {
            console.error('二维码生成失败:', error);
            element.innerHTML = '<div style="color: red; text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background: #fff5f5;">❌ 二维码生成失败<br/><small>' + error.message + '</small></div>';
        }
    }, 50); // 增加延迟时间
}

// 生成二维码到img元素的函数 (创建div容器然后获取img)
function generateQRCodeToImage(text, imgElementId, options = {}) {
    const img = document.getElementById(imgElementId);
    if (!img) {
        console.error('找不到图片元素:', imgElementId);
        return;
    }
    
    // 检查QRCode库是否可用
    if (!checkQRCodeLibrary()) {
        console.error('QRCode库未加载');
        img.alt = 'QRCode库未加载';
        img.style.border = '1px solid red';
        return;
    }
    
    try {
        // 创建临时div容器
        const tempDiv = document.createElement('div');
        tempDiv.style.display = 'none';
        document.body.appendChild(tempDiv);
        
        const qrOptions = {
            text: text,
            width: options.width || 200,
            height: options.height || 200,
            colorDark: options.darkColor || '#000000',
            colorLight: options.lightColor || '#FFFFFF'
        };
        
        // 创建二维码
        const qr = new QRCode(tempDiv, qrOptions);
        
        // 等待二维码生成完成后获取图片
        setTimeout(() => {
            const qrImg = tempDiv.querySelector('img');
            if (qrImg && qrImg.src) {
                img.src = qrImg.src;
                img.alt = '二维码';
                console.log('二维码生成成功:', imgElementId);
            } else {
                img.alt = '二维码生成失败';
                img.style.border = '1px solid red';
                console.error('无法获取生成的二维码图片');
            }
            // 清理临时元素
            if (document.body.contains(tempDiv)) {
                document.body.removeChild(tempDiv);
            }
        }, 200);
        
    } catch (error) {
        console.error('二维码生成失败:', error);
        img.alt = '二维码生成失败: ' + error.message;
        img.style.border = '1px solid red';
    }
}

// 检查QRCode库是否加载完成
function checkQRCodeLibrary() {
    return typeof QRCode !== 'undefined';
}

// 等待QRCode库加载完成后执行回调
function waitForQRCode(callback, maxWait = 5000) {
    const startTime = Date.now();
    
    function check() {
        if (checkQRCodeLibrary()) {
            callback();
        } else if (Date.now() - startTime < maxWait) {
            setTimeout(check, 100);
        } else {
            console.error('QRCode库加载超时');
        }
    }
    
    check();
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('视频处理工具已加载');
    
    // 等待QRCode库加载完成后生成二维码
    waitForQRCode(function() {
        console.log('QRCode库已加载，开始生成二维码');
        
        // 自动生成页面中的二维码
        const qrElements = document.querySelectorAll('[data-qr-text]');
        qrElements.forEach(function(element) {
            const text = element.getAttribute('data-qr-text');
            let width = parseInt(element.getAttribute('data-qr-width')) || 200;
            let height = parseInt(element.getAttribute('data-qr-height')) || 200;
            
            // 根据屏幕宽度调整二维码尺寸
            const screenWidth = window.innerWidth;
            if (screenWidth <= 480) {
                // 小屏幕手机
                width = Math.min(width, 130);
                height = Math.min(height, 130);
            } else if (screenWidth <= 768) {
                // 一般移动设备
                width = Math.min(width, 160);
                height = Math.min(height, 160);
            } else {
                // PC端保持原始大小，或者稍微调整
                width = Math.max(width, 180); // PC端确保最小尺寸
                height = Math.max(height, 180);
                console.log('PC端二维码尺寸:', width, 'x', height);
            }
            
            if (element.tagName.toLowerCase() === 'div') {
                generateQRCode(text, element.id, {width: width, height: height});
            } else if (element.tagName.toLowerCase() === 'img') {
                generateQRCodeToImage(text, element.id, {width: width, height: height});
            }
        });
    });
});

// 重新生成所有二维码的函数
function regenerateAllQRCodes() {
    // 等待QRCode库加载完成后重新生成二维码
    waitForQRCode(function() {
        console.log('重新生成所有二维码');
        
        // 重新生成页面中的二维码
        const qrElements = document.querySelectorAll('[data-qr-text]');
        qrElements.forEach(function(element) {
            // 清除已生成标记，允许重新生成
            element.dataset.qrGenerated = 'false';
            
            const text = element.getAttribute('data-qr-text');
            let width = parseInt(element.getAttribute('data-qr-width')) || 200;
            let height = parseInt(element.getAttribute('data-qr-height')) || 200;
            
            // 根据屏幕宽度调整二维码尺寸
            const screenWidth = window.innerWidth;
            if (screenWidth <= 480) {
                // 小屏幕手机
                width = Math.min(width, 130);
                height = Math.min(height, 130);
            } else if (screenWidth <= 768) {
                // 一般移动设备
                width = Math.min(width, 160);
                height = Math.min(height, 160);
            } else {
                // PC端保持原始大小，或者稍微调整
                width = Math.max(width, 180); // PC端确保最小尺寸
                height = Math.max(height, 180);
                console.log('PC端二维码尺寸:', width, 'x', height);
            }
            
            if (element.tagName.toLowerCase() === 'div') {
                generateQRCode(text, element.id, {width: width, height: height});
            } else if (element.tagName.toLowerCase() === 'img') {
                generateQRCodeToImage(text, element.id, {width: width, height: height});
            }
        });
    });
}

// 窗口大小改变时重新生成二维码（暂时禁用以避免重复生成）
/*
let resizeTimeout;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(function() {
        regenerateAllQRCodes();
    }, 300); // 防抖动，300ms后执行
});
*/

// 下载二维码的函数
function downloadQRCode(elementId) {
    const element = document.getElementById(elementId);
    if (!element) {
        alert('找不到二维码元素');
        return;
    }
    
    // 查找二维码图片元素 (qrcodejs生成的img在div中)
    let qrImg = element;
    if (element.tagName.toLowerCase() === 'div') {
        qrImg = element.querySelector('img');
    }
    
    if (!qrImg || !qrImg.src) {
        alert('二维码还未生成，请稍等...');
        return;
    }
    
    // 创建一个临时的 canvas 来获取二维码图像数据
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    // 等待图片加载完成
    const tempImg = new Image();
    tempImg.onload = function() {
        canvas.width = this.width;
        canvas.height = this.height;
        ctx.drawImage(this, 0, 0);
        
        // 创建下载链接
        canvas.toBlob(function(blob) {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'qrcode.png';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        });
    };
    tempImg.crossOrigin = 'anonymous'; // 解决跨域问题
    tempImg.src = qrImg.src;
}