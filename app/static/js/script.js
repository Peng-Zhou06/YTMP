// 工具函数：防抖
function debounce(func, wait, immediate) {
    var timeout;
    return function() {
        var context = this, args = arguments;
        var later = function() {
            timeout = null;
            if (!immediate) func.apply(context, args);
        };
        var callNow = immediate && !timeout;
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
        if (callNow) func.apply(context, args);
    };
}

// 工具函数：节流
function throttle(func, limit) {
    var inThrottle;
    return function() {
        var args = arguments;
        var context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(function() { inThrottle = false; }, limit);
        }
    };
}

// 工具函数：图片懒加载
function lazyLoadImages() {
    var images = document.querySelectorAll('img[data-src]');
    if ('IntersectionObserver' in window) {
        var imageObserver = new IntersectionObserver(function(entries, observer) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    var img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });
        images.forEach(function(img) { imageObserver.observe(img); });
    } else {
        images.forEach(function(img) { img.src = img.dataset.src; img.removeAttribute('data-src'); });
    }
}

// Ajax请求处理（优化版）
function ajaxRequest(url, method, data, successCallback, errorCallback) {
    $.ajax({
        url: url,
        method: method,
        data: data,
        dataType: 'json',
        timeout: 10000,
        success: function(response) {
            if (successCallback) successCallback(response);
        },
        error: function(xhr, status, error) {
            if (errorCallback) errorCallback(xhr, status, error);
            else {
                var msg = status === 'timeout' ? '请求超时，请重试' : '请求失败: ' + error;
                alert(msg);
            }
        }
    });
}

// 主逻辑
$(document).ready(function() {
    // 侧边栏切换
    $('#sidebar-toggle').click(function() {
        $('.sidebar').toggleClass('open');
        $('.main').toggleClass('sidebar-open');
    });
    
    // 确认删除
    $('.btn-delete').click(function(e) {
        if (!confirm('确定要删除这条记录吗？')) {
            e.preventDefault();
            return false;
        }
        return true;
    });
    
    // 批量删除确认
    $('.btn-batch-delete').click(function(e) {
        if ($('.checkbox-item:checked').length === 0) {
            alert('请至少选择一条记录');
            e.preventDefault();
            return false;
        }
        if (!confirm('确定要删除选中的记录吗？')) {
            e.preventDefault();
            return false;
        }
        return true;
    });
    
    // 全选/取消全选
    $('.checkbox-all').click(function() {
        $('.checkbox-item').prop('checked', $(this).prop('checked'));
    });
    
    // 单个选择后检查全选状态
    $('.checkbox-item').click(function() {
        if ($('.checkbox-item:checked').length === $('.checkbox-item').length) {
            $('.checkbox-all').prop('checked', true);
        } else {
            $('.checkbox-all').prop('checked', false);
        }
    });
    
    // 文件上传预览
    $('.file-upload').change(function() {
        var fileName = $(this).val().split('\\').pop();
        $(this).next('.file-name').text(fileName);
    });
    
    // 表单验证（优化版）
    $('.form-validate').submit(function(e) {
        var isValid = true;
        var firstInvalidField = null;
        
        $('.form-control').each(function() {
            if ($(this).prop('required') || $(this).attr('aria-required') === 'true') {
                if ($(this).val().trim() === '') {
                    $(this).addClass('is-invalid');
                    isValid = false;
                    if (!firstInvalidField) {
                        firstInvalidField = $(this);
                    }
                } else {
                    $(this).removeClass('is-invalid');
                }
            }
        });
        
        if (!isValid) {
            e.preventDefault();
            if (firstInvalidField) {
                firstInvalidField.focus();
            }
            return false;
        }
        return true;
    });
    
    // 移除表单验证错误状态
    $('.form-control').focus(function() {
        $(this).removeClass('is-invalid');
    });
    
    // 成绩输入验证（防抖）
    $('.score-input').keyup(debounce(function() {
        var score = parseFloat($(this).val());
        if (isNaN(score) || score < 0 || score > 100) {
            $(this).addClass('is-invalid');
        } else {
            $(this).removeClass('is-invalid');
        }
    }, 300));
    
    // 密码强度检查（节流）
    $('#password').keyup(throttle(function() {
        var password = $(this).val();
        var strength = 0;
        
        if (password.length >= 8) strength++;
        if (password.match(/[a-z]/) && password.match(/[A-Z]/)) strength++;
        if (password.match(/[0-9]/)) strength++;
        if (password.match(/[^A-Za-z0-9]/)) strength++;
        
        var strengthText = ['弱', '中', '强', '很强'];
        var strengthClass = ['danger', 'warning', 'primary', 'success'];
        
        $('#password-strength').text('密码强度: ' + strengthText[strength]);
        $('#password-strength').removeClass('text-danger text-warning text-primary text-success');
        $('#password-strength').addClass('text-' + strengthClass[strength]);
    }, 200));
    
    // 确认密码验证
    $('#confirm_password').keyup(function() {
        var password = $('#password').val();
        var confirmPassword = $(this).val();
        
        if (password === confirmPassword) {
            $(this).removeClass('is-invalid');
            $(this).addClass('is-valid');
        } else {
            $(this).removeClass('is-valid');
            $(this).addClass('is-invalid');
        }
    });
    
    // 模态框关闭时重置表单
    $('.modal').on('hidden.bs.modal', function() {
        $(this).find('form')[0].reset();
        $(this).find('.form-control').removeClass('is-invalid is-valid');
    });
    
    // 数据导入进度条
    $('.import-btn').click(function() {
        $('#import-progress').show();
        $('#import-progress-bar').width('0%');
        
        var progress = 0;
        var interval = setInterval(function() {
            progress += 10;
            $('#import-progress-bar').width(progress + '%');
            $('#import-progress-bar').text(progress + '%');
            
            if (progress >= 100) {
                clearInterval(interval);
                $('#import-progress').hide();
            }
        }, 300);
    });
    
    // 导出按钮点击
    $('.export-btn').click(function() {
        var $btn = $(this);
        var originalText = $btn.text();
        $btn.text('导出中...');
        $btn.prop('disabled', true);
        
        setTimeout(function() {
            $btn.text(originalText);
            $btn.prop('disabled', false);
        }, 1500);
    });
    
    // 批量操作下拉菜单
    $('.batch-action').change(function() {
        var action = $(this).val();
        if (action === '' || $('.checkbox-item:checked').length === 0) {
            return;
        }
        
        if (action === 'delete') {
            if (confirm('确定要删除选中的记录吗？')) {
                $('#batch-form').submit();
            }
        } else if (action === 'export') {
            $('#batch-form').attr('action', $(this).data('export-url'));
            $('#batch-form').submit();
        }
        
        $(this).val('');
    });
    
    // 表格排序
    $('.sortable').click(function() {
        var sortField = $(this).data('sort');
        var currentSort = $(this).data('current-sort') || 'asc';
        var newSort = currentSort === 'asc' ? 'desc' : 'asc';
        
        var url = new URL(window.location.href);
        url.searchParams.set('sort', sortField);
        url.searchParams.set('order', newSort);
        
        window.location.href = url.href;
    });
    
    // 搜索框防抖（优化）
    var searchInput = $('.search-box input[type="text"]');
    if (searchInput.length > 0) {
        searchInput.keyup(debounce(function() {
            var value = $(this).val().trim();
            if (value.length > 0 || $(this).data('last-value')) {
                $(this).data('last-value', value);
                $(this).closest('form').submit();
            }
        }, 500));
    }
    
    // 图片懒加载
    lazyLoadImages();
});

// 更新成绩
function updateScore(scoreId, scoreValue) {
    if (isNaN(scoreValue) || scoreValue < 0 || scoreValue > 100) {
        alert('成绩必须在0-100之间');
        return;
    }
    
    ajaxRequest(
        '/scores/' + scoreId + '/update',
        'POST',
        { score: scoreValue },
        function(response) {
            if (response.success) {
                alert('成绩更新成功');
            } else {
                alert('成绩更新失败: ' + response.message);
            }
        }
    );
}

// 删除记录
function deleteRecord(url) {
    if (confirm('确定要删除这条记录吗？')) {
        ajaxRequest(
            url,
            'DELETE',
            {},
            function(response) {
                if (response.success) {
                    window.location.reload();
                } else {
                    alert('删除失败: ' + response.message);
                }
            }
        );
    }
}